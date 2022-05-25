from openupgradelib import openupgrade


def create_account_payment_method_line(env):
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO account_payment_method_line
        (name, payment_method_id, journal_id, payment_account_id)
        SELECT apm.name, apm.id, pa.{0}, aj.{1}
        FROM account_payment_method apm
        JOIN payment_acquirer pa ON pa.provider = apm.code
        JOIN account_journal aj ON aj.id = pa.{0}
        WHERE pa.provider != 'none' AND
        apm.payment_type = 'inbound' AND
        apm.id NOT IN (SELECT payment_method_id FROM account_payment_method_line)
        """.format(
            openupgrade.get_legacy_name("journal_id"),
            openupgrade.get_legacy_name("payment_debit_account_id"),
        ),
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO account_payment_method_line
        (name, payment_method_id, journal_id, payment_account_id)
        SELECT apm.name, apm.id, pa.{0}, aj.{1}
        FROM account_payment_method apm
        JOIN payment_acquirer pa ON pa.provider = apm.code
        JOIN account_journal aj ON aj.id = pa.{0}
        WHERE pa.provider != 'none' AND
        apm.payment_type = 'outbound' AND
        apm.id NOT IN (SELECT payment_method_id FROM account_payment_method_line)
        """.format(
            openupgrade.get_legacy_name("journal_id"),
            openupgrade.get_legacy_name("payment_credit_account_id"),
        ),
    )


@openupgrade.migrate()
def migrate(env, version):
    create_account_payment_method_line(env)
