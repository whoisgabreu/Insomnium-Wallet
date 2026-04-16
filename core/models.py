from django.db import models
from django.contrib.auth.models import User


class Receita(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receitas')
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    descricao = models.CharField(max_length=200, blank=True, default='')
    data = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-created_at']
        verbose_name = 'Receita'
        verbose_name_plural = 'Receitas'

    def __str__(self):
        return f"Receita R${self.valor} em {self.data}"


class GastoFixo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gastos_fixos')
    nome = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    dia_vencimento = models.PositiveSmallIntegerField(default=1, help_text='Dia do mês (1–31)')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Gasto Fixo'
        verbose_name_plural = 'Gastos Fixos'

    def __str__(self):
        return f"{self.nome} — R${self.valor}"


def comprovante_upload_path(instance, filename):
    return f'comprovantes/{instance.usuario.id}/{filename}'


class Despesa(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='despesas')
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    descricao = models.CharField(max_length=200)
    data = models.DateField()
    comprovante = models.FileField(
        upload_to=comprovante_upload_path,
        blank=True,
        null=True,
        help_text='Imagem ou PDF (opcional)'
    )
    gasto_fixo = models.ForeignKey(
        GastoFixo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='despesas_geradas'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-created_at']
        verbose_name = 'Despesa'
        verbose_name_plural = 'Despesas'

    def __str__(self):
        return f"{self.descricao} — R${self.valor} em {self.data}"
