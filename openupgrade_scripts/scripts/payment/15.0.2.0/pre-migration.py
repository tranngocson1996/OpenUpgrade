from openupgradelib import openupgrade


def copy_fields(env):
    openupgrade.copy_columns(
        env.cr,
        {
            "payment_acquirer": [
                ("journal_id", None, None),
            ],
        },
    )


def fast_fill_payment_token_name(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_token
        SET name = 'XXXXXXXXXX????'
        WHERE name IS NULL""",
    )


def fast_fill_payment_transaction_partner_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE payment_transaction pt
        SET partner_id = (SELECT ap.partner_id
            FROM account_payment ap
            WHERE pt.partner_id IS NULL AND
            ap.payment_transaction_id = pt.id
            LIMIT 1)""",
    )


@openupgrade.migrate()
def migrate(env, version):
    copy_fields(env)
    fast_fill_payment_token_name(env)
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
    fast_fill_payment_transaction_partner_id(env)
