"""Phase F1: seed missing ir.model.fields.selection records for state=base fields.
Odoo blocks XML/ORM writes to state=base field selections. This migration uses
direct SQL to bypass that restriction — safe because our tuples come from
CDB's ground truth and match the Python selection= tuples in fields.Selection().
"""

def migrate(cr, version):
    if not version:
        return
    # (model, field_name, value, display_name, sequence)
    data = [
        ('helpdesk.ticket', 'x_studio_tracking', 'serial', 'By Unique Serial Number', 10),
        ('helpdesk.ticket', 'x_studio_tracking', 'lot', 'By Lots', 1),
        ('helpdesk.ticket', 'x_studio_tracking', 'none', 'No Tracking', 2),
    ]
    for model, name, value, display, seq in data:
        cr.execute("""
            INSERT INTO ir_model_fields_selection
                (field_id, value, name, sequence, create_uid, create_date, write_uid, write_date)
            SELECT f.id, %s, %s, %s, 1, NOW() AT TIME ZONE 'UTC', 1, NOW() AT TIME ZONE 'UTC'
            FROM ir_model_fields f
            WHERE f.model = %s AND f.name = %s AND NOT EXISTS (
                SELECT 1 FROM ir_model_fields_selection s
                WHERE s.field_id = f.id AND s.value = %s
            )
        """, (value, display, seq, model, name, value))