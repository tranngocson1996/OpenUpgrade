from openupgradelib import openupgrade


def convert_field_to_html(env):
    openupgrade.convert_field_to_html(
        env.cr, "res_company", "invoice_terms", "invoice_terms"
    )
    openupgrade.convert_field_to_html(env.cr, "account_fiscal_position", "note", "note")
    openupgrade.convert_field_to_html(env.cr, "account_move", "narration", "narration")
    openupgrade.convert_field_to_html(env.cr, "account_payment_term", "note", "note")


def fast_fill_account_move_always_tax_exigible(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS always_tax_exigible boolean""",
    )
    # record.is_invoice(True) is True
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET always_tax_exigible = false
        WHERE move_type IN (
            'out_invoice',
            'out_refund',
            'in_refund',
            'in_invoice',
            'out_receipt',
            'in_receipt')""",
    )
    # record._collect_tax_cash_basis_values() is False
    # 1. not values['to_process_lines'] or not has_term_lines
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move am
        SET always_tax_exigible =
            CASE
                WHEN
                    (SELECT COUNT(aml.id)
                    FROM account_move_line aml
                    JOIN account_account aa ON aa.id = aml.account_id
                    JOIN account_account_type aat ON aat.id = aa.user_type_id
                    WHERE aml.move_id = am.id AND
                    aat.type IN ('receivable', 'payable')) = 0
                    OR NOT
                    (
                        (SELECT COUNT(aml.id)
                        FROM account_move_line aml
                        JOIN account_tax at ON at.id = aml.tax_line_id
                        WHERE aml.move_id = am.id AND
                        at.tax_exigibility = 'on_payment') > 0
                        OR
                        'on_payment' IN (
                            SELECT at.tax_exigibility
                            FROM account_move_line aml
                            JOIN account_move_line_account_tax_rel ataml
                                ON ataml.account_move_line_id = aml.id
                            JOIN account_tax at ON at.id = ataml.account_tax_id
                            WHERE aml.move_id = am.id
                        )
                    )
                THEN true
            END
        WHERE am.always_tax_exigible IS NULL""",
    )
    # 2. len(currencies) != 1
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move am
        SET always_tax_exigible =
            CASE
                WHEN (SELECT COUNT(aml.currency_id)
                     FROM account_move_line aml
                     WHERE aml.move_id = am.id) != 1
                THEN true
                ELSE false
            END
        WHERE am.always_tax_exigible IS NULL""",
    )


def fast_fill_account_move_amount_total_in_currency_signed(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_move
        ADD COLUMN IF NOT EXISTS amount_total_in_currency_signed float""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move
        SET amount_total_in_currency_signed =
            CASE
                WHEN move_type = 'entry'
                THEN ABS(amount_total)
                WHEN move_type IN ('in_invoice', 'out_refund', 'in_receipt')
                THEN -amount_total
                ELSE amount_total
                END""",
    )


def fast_fill_account_move_line_tax_tag_invert(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS tax_tag_invert boolean""",
    )
    # 1.Invoices imported from other softwares might only have kept the tags, not the taxes
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move_line aml
        SET tax_tag_invert =
            CASE
                WHEN (SELECT COUNT(account_account_tag_id)
                    FROM account_account_tag_account_move_line_rel
                    WHERE aml.id = account_move_line_id) > 0
                THEN am.move_type IN ('out_invoice', 'in_refund', 'out_receipt')
                END
        FROM account_move am
        WHERE tax_repartition_line_id IS NULL AND
        (SELECT COUNT(account_tax_id)
            FROM account_move_line_account_tax_rel
            WHERE aml.id = account_move_line_id) = 0 AND
        am.id = aml.move_id""",
    )
    # 2.For misc operations,
    # cash basis entries and write-offs from the bank reconciliation widget
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move_line aml
        SET tax_tag_invert =
            CASE
                WHEN (SELECT COALESCE(refund_tax.type_tax_use, invoice_tax.type_tax_use)
                    FROM account_tax_repartition_line atpl
                    JOIN account_tax refund_tax ON refund_tax.id = refund_tax_id
                    JOIN account_tax invoice_tax ON invoice_tax.id = invoice_tax_id
                    WHERE atpl.id = aml.tax_repartition_line_id) = 'purchase'
                THEN (SELECT refund_tax_id
                    FROM account_tax_repartition_line
                    WHERE id = aml.tax_repartition_line_id) IS NOT NULL
                WHEN (SELECT COALESCE(refund_tax.type_tax_use, invoice_tax.type_tax_use)
                    FROM account_tax_repartition_line atpl
                    JOIN account_tax refund_tax ON refund_tax.id = refund_tax_id
                    JOIN account_tax invoice_tax ON invoice_tax.id = invoice_tax_id
                    WHERE atpl.id = aml.tax_repartition_line_id) = 'sale'
                THEN (SELECT refund_tax_id
                    FROM account_tax_repartition_line
                    WHERE id = aml.tax_repartition_line_id) IS NULL
            END
        FROM account_move am
        WHERE am.id = aml.move_id AND
        am.move_type = 'entry' AND
        aml.tax_tag_invert IS NULL AND
        aml.tax_repartition_line_id IS NOT NULL""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move_line aml
        SET tax_tag_invert =
            CASE
                WHEN (SELECT at.type_tax_use
                    FROM account_move_line_account_tax_rel
                    JOIN account_tax at ON at.id = account_tax_id
                    WHERE aml.id = account_move_line_id
                    LIMIT 1) = 'purchase'
                THEN aml.credit > 0
                WHEN (SELECT at.type_tax_use
                    FROM account_move_line_account_tax_rel
                    JOIN account_tax at ON at.id = account_tax_id
                    WHERE aml.id = account_move_line_id
                    LIMIT 1) = 'sale'
                THEN aml.debit > 0
            END
        FROM account_move am
        WHERE am.id = aml.move_id AND
        am.move_type = 'entry' AND
        aml.tax_tag_invert IS NULL AND
        (SELECT COUNT(account_tax_id)
            FROM account_move_line_account_tax_rel
            WHERE aml.id = account_move_line_id) > 0""",
    )
    # 3.For invoices with taxes
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_move_line aml
        SET tax_tag_invert = am.move_type IN ('out_invoice', 'in_refund', 'out_receipt')
        FROM account_move am
        WHERE am.id = aml.move_id AND
        aml.tax_tag_invert IS NULL""",
    )


def create_account_payment_method_line(env):
    # Create account_payment_method_line table
    openupgrade.logged_query(
        env.cr,
        """
        CREATE TABLE account_payment_method_line (
            id SERIAL,
            journal_id int,
            name varchar,
            payment_account_id int,
            payment_method_id int NOT NULL,
            sequence int,
            CONSTRAINT account_payment_method_line_pkey PRIMARY KEY (id)
        )""",
    )
    # Create account payment method lines from account payment methods
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO account_payment_method_line
        (name, payment_method_id, journal_id, payment_account_id, sequence)
        SELECT apm.name, apm.id, aj.id, aj.payment_debit_account_id, 10
        FROM account_payment_method apm
        JOIN account_journal_inbound_payment_method_rel ajipm
            ON apm.id = ajipm.inbound_payment_method
        JOIN account_journal aj ON aj.id = ajipm.journal_id
        WHERE aj.type IN ('bank', 'cash') AND
        apm.payment_type = 'inbound'""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO account_payment_method_line
        (name, payment_method_id, journal_id, payment_account_id, sequence)
        SELECT apm.name, apm.id, aj.id, aj.payment_credit_account_id, 10
        FROM account_payment_method apm
        JOIN account_journal_outbound_payment_method_rel ajopm
            ON apm.id = ajopm.outbound_payment_method
        JOIN account_journal aj ON aj.id = ajopm.journal_id
        WHERE aj.type IN ('bank', 'cash') AND
        apm.payment_type = 'outbound'""",
    )


def fast_fill_account_reconcile_model_payment_tolerance_type(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_reconcile_model
        ADD COLUMN IF NOT EXISTS payment_tolerance_type varchar""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_reconcile_model
        SET payment_tolerance_type = 'percentage'""",
    )


def fast_fill_account_reconcile_model_payment_tolerance_param(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_reconcile_model
        ADD COLUMN IF NOT EXISTS payment_tolerance_param float""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_reconcile_model
        SET payment_tolerance_type = 0.0""",
    )


def fast_fill_account_reconcile_model_template_payment_tolerance_type(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_reconcile_model_template
        ADD COLUMN IF NOT EXISTS payment_tolerance_type varchar""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_reconcile_model_template
        SET payment_tolerance_type = 'percentage'""",
    )


def fast_fill_account_payment_payment_method_line_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_payment
        ADD COLUMN IF NOT EXISTS payment_method_line_id int""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment ap
        SET payment_method_line_id =
        CASE
            WHEN (SELECT count(apml.id)
                FROM account_payment_method apm
                JOIN account_payment_method_line apml
                    ON apml.payment_method_id = apm.id
                WHERE apm.payment_type = ap.payment_type AND
                am.journal_id = apml.journal_id) > 0
            THEN (SELECT apml.id
                FROM account_payment_method apm
                JOIN account_payment_method_line apml
                    ON apml.payment_method_id = apm.id
                WHERE apm.payment_type = ap.payment_type AND
                am.journal_id = apml.journal_id
                LIMIT 1)
        END
        FROM account_move am
        WHERE am.id = ap.move_id""",
    )


def fast_fill_account_payment_outstanding_account_id(env):
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE account_payment
        ADD COLUMN IF NOT EXISTS outstanding_account_id int""",
    )
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_payment ap
        SET outstanding_account_id = apml.payment_account_id
        FROM account_payment_method_line apml
        WHERE ap.payment_method_line_id = apml.id""",
    )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.set_xml_ids_noupdate_value(
        env, "account", ["action_account_resequence"], True
    )
    openupgrade.rename_columns(
        env.cr,
        {
            "account_move": [
                ("tax_cash_basis_move_id", "tax_cash_basis_origin_move_id"),
            ],
        },
    )
    convert_field_to_html(env)
    fast_fill_account_move_always_tax_exigible(env)
    fast_fill_account_move_amount_total_in_currency_signed(env)
    fast_fill_account_move_line_tax_tag_invert(env)
    create_account_payment_method_line(env)
    fast_fill_account_reconcile_model_payment_tolerance_type(env)
    fast_fill_account_reconcile_model_payment_tolerance_param(env)
    fast_fill_account_reconcile_model_template_payment_tolerance_type(env)
    fast_fill_account_payment_payment_method_line_id(env)
    fast_fill_account_payment_outstanding_account_id(env)
