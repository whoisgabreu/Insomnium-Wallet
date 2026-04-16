import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Max
from django.db.models.functions import TruncMonth
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import RegistroForm, LoginForm, ReceitaForm, DespesaForm, GastoFixoForm
from .models import Receita, Despesa, GastoFixo


# ─────────────────────────── AUTH ───────────────────────────


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Bem-vindo de volta, {user.first_name or user.username}!')
        return redirect('dashboard')
    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Conta criada! Boas-vindas, {user.first_name or user.username}!')
        return redirect('dashboard')
    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Você saiu da sua conta.')
    return redirect('login')


# ─────────────────────────── DASHBOARD ───────────────────────────


def _calcular_alerta(receita_mes, total_gasto_mes, hoje):
    """
    Modelo de saldo acumulado:
    Se o usuário 'poupou' dias, pode gastar mais em um único dia sem alerta.
    Compara total gasto no mês vs. orçamento acumulado proporcional ao dia atual.
    """
    if not receita_mes or receita_mes == 0:
        return None

    dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
    dias_passados = hoje.day
    orcamento_diario = receita_mes / Decimal(dias_no_mes)
    orcamento_acumulado = orcamento_diario * Decimal(dias_passados)

    if orcamento_acumulado == 0:
        return None

    percentual = (total_gasto_mes / orcamento_acumulado) * 100
    saldo_disponivel = orcamento_acumulado - total_gasto_mes

    if total_gasto_mes > orcamento_acumulado:
        return {
            'nivel': 'vermelho',
            'titulo': '⚠️ Orçamento Estourado!',
            'mensagem': f'Você gastou R$ {total_gasto_mes:,.2f} mas seu orçamento acumulado até hoje é '
                        f'R$ {orcamento_acumulado:,.2f}. Reduza seus gastos imediatamente.',
            'percentual': float(percentual),
            'saldo': float(saldo_disponivel),
            'orcamento_acumulado': float(orcamento_acumulado),
        }
    elif total_gasto_mes > orcamento_acumulado * Decimal('0.85'):
        return {
            'nivel': 'amarelo',
            'titulo': '🔔 Atenção ao Orçamento',
            'mensagem': f'Você usou {percentual:.0f}% do orçamento acumulado. '
                        f'Ainda tem R$ {saldo_disponivel:,.2f} de margem.',
            'percentual': float(percentual),
            'saldo': float(saldo_disponivel),
            'orcamento_acumulado': float(orcamento_acumulado),
        }
    return {
        'nivel': 'verde',
        'titulo': '✅ Finanças em Ordem',
        'mensagem': f'Você usou {percentual:.0f}% do orçamento acumulado. '
                    f'Ainda tem R$ {saldo_disponivel:,.2f} disponível.',
        'percentual': float(percentual),
        'saldo': float(saldo_disponivel),
        'orcamento_acumulado': float(orcamento_acumulado),
    }


@login_required
def dashboard_view(request):
    hoje = date.today()
    usuario = request.user

    # ── Totais all-time ──
    total_gasto_alltime = Despesa.objects.filter(usuario=usuario).aggregate(
        t=Sum('valor'))['t'] or Decimal('0')
    total_receita_alltime = Receita.objects.filter(usuario=usuario).aggregate(
        t=Sum('valor'))['t'] or Decimal('0')
    saldo_total_conta = total_receita_alltime - total_gasto_alltime

    # ── Mês atual ──
    despesas_mes = Despesa.objects.filter(
        usuario=usuario, data__year=hoje.year, data__month=hoje.month)
    receitas_mes = Receita.objects.filter(
        usuario=usuario, data__year=hoje.year, data__month=hoje.month)

    total_gasto_mes = despesas_mes.aggregate(t=Sum('valor'))['t'] or Decimal('0')
    total_receita_mes = receitas_mes.aggregate(t=Sum('valor'))['t'] or Decimal('0')

    saldo_mes = total_receita_mes - total_gasto_mes
    percentual_gasto = (
        (total_gasto_mes / total_receita_mes * 100) if total_receita_mes > 0 else Decimal('0')
    )

    # ── Dia com maior gasto (mês atual) ──
    from django.db.models import Sum as S
    dia_maior_gasto = (
        despesas_mes.values('data')
        .annotate(total_dia=S('valor'))
        .order_by('-total_dia')
        .first()
    )

    # ── Gastos agrupados por mês (últimos 12 meses) ──
    gastos_por_mes = (
        Despesa.objects
        .filter(usuario=usuario)
        .annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(total=Sum('valor'))
        .order_by('-mes')[:12]
    )
    receitas_por_mes = (
        Receita.objects
        .filter(usuario=usuario)
        .annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(total=Sum('valor'))
        .order_by('-mes')[:12]
    )

    # ── Alerta de risco financeiro ──
    alerta = _calcular_alerta(total_receita_mes, total_gasto_mes, hoje)

    # ── Últimas transações ──
    ultimas_despesas = Despesa.objects.filter(usuario=usuario).select_related('gasto_fixo')[:6]
    ultimas_receitas = Receita.objects.filter(usuario=usuario)[:4]

    # ── Gráfico: labels e dados ──
    meses_labels = []
    meses_gastos = []
    meses_receitas = []

    gastos_dict = {g['mes'].strftime('%Y-%m'): float(g['total']) for g in gastos_por_mes}
    receitas_dict = {r['mes'].strftime('%Y-%m'): float(r['total']) for r in receitas_por_mes}

    for i in range(11, -1, -1):
        if i == 0:
            m = hoje.replace(day=1)
        else:
            m = (hoje.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        key = m.strftime('%Y-%m')
        meses_labels.append(m.strftime('%b/%y'))
        meses_gastos.append(gastos_dict.get(key, 0))
        meses_receitas.append(receitas_dict.get(key, 0))

    context = {
        'hoje': hoje,
        'total_gasto_alltime': total_gasto_alltime,
        'total_receita_alltime': total_receita_alltime,
        'saldo_total_conta': saldo_total_conta,
        'total_gasto_mes': total_gasto_mes,
        'total_receita_mes': total_receita_mes,
        'saldo_mes': saldo_mes,
        'percentual_gasto': percentual_gasto,
        'dia_maior_gasto': dia_maior_gasto,
        'alerta': alerta,
        'ultimas_despesas': ultimas_despesas,
        'ultimas_receitas': ultimas_receitas,
        'gastos_por_mes': list(gastos_por_mes),
        'meses_labels': meses_labels,
        'meses_gastos': meses_gastos,
        'meses_receitas': meses_receitas,
    }
    return render(request, 'dashboard.html', context)


# ─────────────────────────── RECEITAS ───────────────────────────


@login_required
def receita_list(request):
    receitas = Receita.objects.filter(usuario=request.user)
    total = receitas.aggregate(t=Sum('valor'))['t'] or Decimal('0')
    por_mes = (
        receitas.annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(total=Sum('valor'))
        .order_by('-mes')
    )
    return render(request, 'receitas/list.html', {
        'receitas': receitas,
        'total': total,
        'por_mes': por_mes,
    })


@login_required
def receita_create(request):
    form = ReceitaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        receita = form.save(commit=False)
        receita.usuario = request.user
        receita.save()
        messages.success(request, f'Receita de R$ {receita.valor:,.2f} registrada com sucesso!')
        return redirect('receita_list')
    return render(request, 'receitas/form.html', {'form': form, 'titulo': 'Nova Receita'})


@login_required
def receita_update(request, pk):
    receita = get_object_or_404(Receita, pk=pk, usuario=request.user)
    form = ReceitaForm(request.POST or None, instance=receita)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Receita atualizada!')
        return redirect('receita_list')
    return render(request, 'receitas/form.html', {'form': form, 'titulo': 'Editar Receita', 'obj': receita})


@login_required
def receita_delete(request, pk):
    receita = get_object_or_404(Receita, pk=pk, usuario=request.user)
    if request.method == 'POST':
        receita.delete()
        messages.success(request, 'Receita removida.')
        return redirect('receita_list')
    return render(request, 'confirm_delete.html', {'obj': receita, 'tipo': 'Receita', 'back_url': 'receita_list'})


# ─────────────────────────── DESPESAS ───────────────────────────


@login_required
def despesa_list(request):
    mes = request.GET.get('mes')
    ano = request.GET.get('ano')
    hoje = date.today()

    if mes and ano:
        try:
            mes, ano = int(mes), int(ano)
        except ValueError:
            mes, ano = hoje.month, hoje.year
    else:
        mes, ano = hoje.month, hoje.year

    despesas = Despesa.objects.filter(
        usuario=request.user, data__year=ano, data__month=mes
    ).select_related('gasto_fixo')

    total_mes = despesas.aggregate(t=Sum('valor'))['t'] or Decimal('0')

    # Navegação entre meses
    meses_disponiveis = (
        Despesa.objects.filter(usuario=request.user)
        .annotate(mes=TruncMonth('data'))
        .values('mes')
        .distinct()
        .order_by('-mes')
    )

    return render(request, 'despesas/list.html', {
        'despesas': despesas,
        'total_mes': total_mes,
        'mes_atual': mes,
        'ano_atual': ano,
        'meses_disponiveis': meses_disponiveis,
        'mes_nome': date(ano, mes, 1).strftime('%B de %Y'),
    })


@login_required
def despesa_create(request):
    form = DespesaForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        despesa = form.save(commit=False)
        despesa.usuario = request.user
        despesa.save()
        messages.success(request, f'Despesa "{despesa.descricao}" registrada!')
        return redirect('despesa_list')
    return render(request, 'despesas/form.html', {'form': form, 'titulo': 'Nova Despesa'})


@login_required
def despesa_update(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk, usuario=request.user)
    form = DespesaForm(request.POST or None, request.FILES or None, instance=despesa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Despesa atualizada!')
        return redirect('despesa_list')
    return render(request, 'despesas/form.html', {'form': form, 'titulo': 'Editar Despesa', 'obj': despesa})


@login_required
def despesa_delete(request, pk):
    despesa = get_object_or_404(Despesa, pk=pk, usuario=request.user)
    if request.method == 'POST':
        despesa.delete()
        messages.success(request, 'Despesa removida.')
        return redirect('despesa_list')
    return render(request, 'confirm_delete.html', {'obj': despesa, 'tipo': 'Despesa', 'back_url': 'despesa_list'})


# ─────────────────────────── GASTOS FIXOS ───────────────────────────


@login_required
def gasto_fixo_list(request):
    hoje = date.today()
    gastos = list(GastoFixo.objects.filter(usuario=request.user))
    
    gastos_lancados_ids = set(Despesa.objects.filter(
        usuario=request.user,
        gasto_fixo__in=gastos,
        data__year=hoje.year,
        data__month=hoje.month
    ).values_list('gasto_fixo_id', flat=True))
    
    for g in gastos:
        g.ja_lancado = g.id in gastos_lancados_ids

    total_ativos = sum((g.valor for g in gastos if g.ativo), Decimal('0'))
    
    return render(request, 'gastos_fixos/list.html', {
        'gastos': gastos,
        'total_ativos': total_ativos,
    })


@login_required
def gasto_fixo_create(request):
    form = GastoFixoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        gf = form.save(commit=False)
        gf.usuario = request.user
        gf.save()
        messages.success(request, f'Gasto fixo "{gf.nome}" cadastrado!')
        return redirect('gasto_fixo_list')
    return render(request, 'gastos_fixos/form.html', {'form': form, 'titulo': 'Novo Gasto Fixo'})


@login_required
def gasto_fixo_update(request, pk):
    gf = get_object_or_404(GastoFixo, pk=pk, usuario=request.user)
    form = GastoFixoForm(request.POST or None, instance=gf)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'"{gf.nome}" atualizado!')
        return redirect('gasto_fixo_list')
    return render(request, 'gastos_fixos/form.html', {'form': form, 'titulo': 'Editar Gasto Fixo', 'obj': gf})


@login_required
def gasto_fixo_delete(request, pk):
    gf = get_object_or_404(GastoFixo, pk=pk, usuario=request.user)
    if request.method == 'POST':
        gf.delete()
        messages.success(request, 'Gasto fixo removido.')
        return redirect('gasto_fixo_list')
    return render(request, 'confirm_delete.html', {'obj': gf, 'tipo': 'Gasto Fixo', 'back_url': 'gasto_fixo_list'})


@login_required
def gasto_fixo_aplicar(request, pk):
    """Lança o gasto fixo como uma despesa do mês atual."""
    gf = get_object_or_404(GastoFixo, pk=pk, usuario=request.user)
    hoje = date.today()

    # Verifica se já foi lançado no mês atual
    ja_lancado = Despesa.objects.filter(
        usuario=request.user,
        gasto_fixo=gf,
        data__year=hoje.year,
        data__month=hoje.month
    ).exists()

    if request.method == 'POST':
        if ja_lancado and not request.POST.get('forcar'):
            messages.warning(request, f'"{gf.nome}" já foi lançado neste mês. Confirme para lançar novamente.')
            return render(request, 'gastos_fixos/confirmar_aplicar.html', {'gf': gf, 'ja_lancado': True})

        # Calcular data de vencimento no mês atual
        dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
        dia = min(gf.dia_vencimento, dias_no_mes)
        data_despesa = date(hoje.year, hoje.month, dia)

        Despesa.objects.create(
            usuario=request.user,
            valor=gf.valor,
            descricao=gf.nome,
            data=data_despesa,
            gasto_fixo=gf,
        )
        messages.success(request, f'"{gf.nome}" lançado como despesa de {hoje.strftime("%B/%Y")}!')
        return redirect('gasto_fixo_list')

    return render(request, 'gastos_fixos/confirmar_aplicar.html', {'gf': gf, 'ja_lancado': ja_lancado})
