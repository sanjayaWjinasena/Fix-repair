"""Phase F1: seed ir.model.fields.selection records for state=base fields via SQL.
Odoo 17: `name` column is JSONB (translation) - must be JSON-encoded, not plain str."""
import json

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
        # Name is a JSONB translation field in Odoo 17
        name_json = json.dumps({"en_US": display})
        cr.execute("""
            INSERT INTO ir_model_fields_selection
                (field_id, value, name, sequence, create_uid, create_date, write_uid, write_date)
            SELECT f.id, %s, %s::jsonb, %s, 1, NOW() AT TIME ZONE 'UTC', 1, NOW() AT TIME ZONE 'UTC'
            FROM ir_model_fields f
            WHERE f.model = %s AND f.name = %s AND NOT EXISTS (
                SELECT 1 FROM ir_model_fields_selection s
                WHERE s.field_id = f.id AND s.value = %s
            )
        """, (value, name_json, seq, model, name, value))