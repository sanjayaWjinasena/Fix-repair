# -*- coding: utf-8 -*-
"""
helpdesk.create.fsm.task — assign the Plan-Intervention user as the
task's assignee.

Plan Intervention on a helpdesk-repair ticket opens the
helpdesk.create.fsm.task pre-fill wizard. The wizard's Create Task
buttons create a project.task record but leave user_ids empty by
default. The user who clicked Plan Intervention is a natural
default assignee — they're taking ownership of the intervention.

Override both Create buttons to post-process the created task and
stamp user_ids = current user. project.task.create_date is already
auto-set by the ORM at record-creation time, so no explicit
handling is needed for the "Created Date" side of the request.
"""
from odoo import models


class HelpdeskCreateFsmTask(models.TransientModel):
    _inherit = 'helpdesk.create.fsm.task'

    def action_generate_task(self):
        result = super().action_generate_task()
        self._stamp_assignees_on_created_task(result)
        return result

    def action_generate_and_view_task(self):
        result = super().action_generate_and_view_task()
        self._stamp_assignees_on_created_task(result)
        return result

    def _stamp_assignees_on_created_task(self, result):
        """When the caller's action returns an act_window pointing at
        a project.task record, add the current user to the task's
        user_ids. Uses (4, uid) so any assignees the wizard may have
        set stay in place — we only ADD, never replace.
        """
        if not isinstance(result, dict):
            return
        if result.get('res_model') != 'project.task':
            return
        task_id = result.get('res_id')
        if not task_id:
            return
        task = self.env['project.task'].browse(task_id).exists()
        if not task:
            return
        task.write({'user_ids': [(4, self.env.uid)]})
