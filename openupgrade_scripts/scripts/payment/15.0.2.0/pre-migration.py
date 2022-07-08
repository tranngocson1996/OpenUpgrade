from openupgradelib import openupgrade


def fast_fill_payment_token_name(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_token
        SET name = 'XXXXXXXXXX????'
        WHERE name IS NULL""",
    )


def fast_fill_payment_transaction_partner_id(env):
    # 1. fill value from partner in payment
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_transaction pt
        SET partner_id = ap.partner_id
        FROM account_payment ap
        WHERE pt.partner_id IS NULL
            AND ap.partner_id IS NOT NULL
            AND ap.id = pt.payment_id
        """,
    )
    # 2. fill value from partner in payment token
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_transaction pt
        SET partner_id = pto.partner_id
        FROM payment_token pto
        WHERE pt.partner_id IS NULL
            AND pto.id = pt.payment_token_id
        """,
    )
    # 3. fill value from partner in account move
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_transaction pt
        SET partner_id = am.partner_id
        FROM account_invoice_transaction_rel ait
        JOIN account_move am ON am.id = ait.invoice_id
        WHERE pt.partner_id IS NULL
            AND ait.transaction_id = pt.id
            AND am.partner_id IS NOT NULL
        """,
    )


@openupgrade.migrate()
def migrate(env, version):
    fast_fill_payment_token_name(env)
    fast_fill_payment_transaction_partner_id(env)
    openupgrade.rename_fields(
        env,
        [
            (
                "payment.token",
                "payment_token",
                "payment_ids",
                "transaction_ids",
            ),
            (
                "payment.transaction",
                "payment_transaction",
                "is_processed",
                "is_post_processed",
            ),
            (
                "payment.transaction",
                "payment_transaction",
                "payment_token_id",
                "token_id",
            ),
        ],
    )
