# -*- coding: utf-8 -*-
{
    'name': 'Fix Repair',
    'version': '17.0.1.0.230',
    'summary': 'Enhancements to the Customer Care - Repair helpdesk workflow',
    'author': 'Jinasena Agricultural Machinery (Pvt) Ltd.',
    'category': 'Helpdesk',
    'license': 'LGPL-3',
    'depends': ['base_setup', 'helpdesk', 'helpdesk_fsm', 'sale', 'sale_stock', 'industry_fsm_sale', 'industry_fsm_stock', 'BugFix-Sales'],
    'post_init_hook': 'post_init_hook',
    'data': [
        'security/ir.model.access.csv',
        'data/fix_repair_data.xml',
        'views/helpdesk_ticket_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'Fix-repair/static/src/scss/task_toast_triggers.scss',
            'Fix-repair/static/src/js/task_missing_data_notifier.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}
