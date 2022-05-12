from openupgradelib import openupgrade


def create_column_hr_leave_holiday_allocation_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_leave
        ADD COLUMN IF NOT EXISTS holiday_allocation_id integer""",
    )


def fast_fill_hr_leave_employee_company_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_leave
        ADD COLUMN IF NOT EXISTS employee_company_id integer""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave hl
        SET employee_company_id = he.company_id
        FROM hr_employee he
        WHERE hl.employee_id = he.id""",
    )


def fast_fill_hr_leave_multi_employee(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_leave
        ADD COLUMN IF NOT EXISTS multi_employee boolean""",
    )
    # When migration to 15.0 set multi_employee field is False
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave hl
        SET multi_employee = False""",
    )


def create_column_hr_leave_allocation_accrual_plan_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_leave_allocation
        ADD COLUMN IF NOT EXISTS accrual_plan_id integer""",
    )


def create_table_hr_employee_hr_leave_allocation(env):
    openupgrade.logged_query(
        env.cr,
        """
        CREATE TABLE IF NOT EXISTS hr_employee_hr_leave_allocation_rel
        (hr_leave_allocation_id INT, hr_employee_id INT)""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO hr_employee_hr_leave_allocation_rel (hr_leave_allocation_id, hr_employee_id)
        SELECT
            CASE
                WHEN holiday_type = 'employee'
                THEN id
                END as hr_leave_allocation_id,
            CASE
                WHEN holiday_type = 'employee'
                THEN employee_id
                END as hr_employee_id
            FROM hr_leave_allocation""",
    )


def map_hr_leave_allocation_state(env):
    openupgrade.logged_query(
        env.cr,
        """UPDATE hr_leave_allocation
        SET state = 'confirm'
        WHERE state = 'validate1'""",
    )


def update_hr_leave_allocation_date_from(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave_allocation hla
        SET date_from = (SELECT MIN(hl.date_from)
        FROM hr_leave hl
        WHERE hl.employee_id = hla.employee_id AND
            hla.allocation_type = 'regular' AND
            hla.state = 'validate')""",
    )


def update_hr_leave_type_allocation_validation_type(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave_type
        SET allocation_validation_type =
            CASE
                WHEN allocation_validation_type in ('both', 'manager')
                THEN 'officer'
                WHEN allocation_validation_type = 'hr'
                THEN 'set'
                END
        WHERE allocation_validation_type IS NOT NULL""",
    )


def fast_fill_hr_leave_type_requires_allocation(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_leave_type
        ADD COLUMN IF NOT EXISTS requires_allocation CHARACTER VARYING""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave_type
        SET requires_allocation =
            CASE
                WHEN allocation_type = 'no'
                THEN 'no'
                ELSE 'yes'
                END""",
    )


def fast_fill_hr_leave_type_employee_requests(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE hr_leave_type
        ADD COLUMN IF NOT EXISTS employee_requests CHARACTER VARYING""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_leave_type
        SET employee_requests =
            CASE
                WHEN leave_validation_type = 'no_validation'
                THEN 'yes'
                ELSE 'no'
                END""",
    )


@openupgrade.migrate()
def migrate(env, version):
    create_column_hr_leave_holiday_allocation_id(env)
    fast_fill_hr_leave_employee_company_id(env)
    fast_fill_hr_leave_multi_employee(env)
    create_column_hr_leave_allocation_accrual_plan_id(env)
    create_table_hr_employee_hr_leave_allocation(env)
    map_hr_leave_allocation_state(env)
    update_hr_leave_allocation_date_from(env)
    update_hr_leave_type_allocation_validation_type(env)
    fast_fill_hr_leave_type_requires_allocation(env)
    fast_fill_hr_leave_type_employee_requests(env)
