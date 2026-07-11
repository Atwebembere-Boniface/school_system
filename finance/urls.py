from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # --- Bursar Routes ---
    path('classes/', views.BursarClassListView.as_view(), name='bursar_class_list'),
    path('student/<int:pk>/finance/', views.StudentFinancialDetailView.as_view(), name='student_finance_detail'),
    path('fees/setup/', views.FeeStructureCreateView.as_view(), name='add_fee_structure'),

    # --- Student Routes ---
    path('my-finance/', views.StudentFinanceDashboardView.as_view(), name='student_dashboard'),
    path('pay/', views.InitiatePaymentView.as_view(), name='pay'),

    # --- Gateway Webhook (External) ---
    path('webhook/callback/', views.payment_webhook, name='payment_webhook'),
    path('class/<int:pk>/students/', views.BursarClassDetailView.as_view(), name='class_student_finance'),
    path('record-payment/', views.BursarRecordPaymentView.as_view(), name='record_payment'),
    path('bursar-dashboard/', views.BursarDashboardView.as_view(), name='bursar_dashboard'),

]