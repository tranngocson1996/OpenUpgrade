from openupgradelib import openupgrade


def fast_fill_hr_leave_holiday_allocation_id(env):
    all_leave = env["hr.leave"].search([])
    all_leave._compute_from_holiday_status_id()


def fast_fill_hr_leave_allocation_accrual_plan_id(env):
    all_leave_allocation = env["hr.leave.allocation"].search([])
    all_leave_allocation._compute_from_holiday_status_id()


@openupgrade.migrate()
def migrate(env, version):
    fast_fill_hr_leave_holiday_allocation_id(env)
    fast_fill_hr_leave_allocation_accrual_plan_id(env)
    openupgrade.load_data(env.cr, "hr_holidays", "15.0.1.5/noupdate_changes.xml")
