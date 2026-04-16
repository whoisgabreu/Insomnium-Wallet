from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Receitas
    path('receitas/', views.receita_list, name='receita_list'),
    path('receitas/nova/', views.receita_create, name='receita_create'),
    path('receitas/<int:pk>/editar/', views.receita_update, name='receita_update'),
    path('receitas/<int:pk>/excluir/', views.receita_delete, name='receita_delete'),

    # Despesas
    path('despesas/', views.despesa_list, name='despesa_list'),
    path('despesas/nova/', views.despesa_create, name='despesa_create'),
    path('despesas/<int:pk>/editar/', views.despesa_update, name='despesa_update'),
    path('despesas/<int:pk>/excluir/', views.despesa_delete, name='despesa_delete'),

    # Gastos Fixos
    path('gastos-fixos/', views.gasto_fixo_list, name='gasto_fixo_list'),
    path('gastos-fixos/novo/', views.gasto_fixo_create, name='gasto_fixo_create'),
    path('gastos-fixos/<int:pk>/editar/', views.gasto_fixo_update, name='gasto_fixo_update'),
    path('gastos-fixos/<int:pk>/excluir/', views.gasto_fixo_delete, name='gasto_fixo_delete'),
    path('gastos-fixos/<int:pk>/aplicar/', views.gasto_fixo_aplicar, name='gasto_fixo_aplicar'),
]
