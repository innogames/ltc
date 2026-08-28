# Django 5.2 upgrade: Meta.index_together was replaced with named
# Meta.indexes (see 0001_initial, edited in place). Existing PostgreSQL
# databases hold the same indexes under the auto-generated index_together
# names — rename them to the new explicit names. Fresh databases already
# created the new names in 0001, so every statement is a guarded no-op.

from django.db import migrations

RENAMES = [
    # (old auto-generated name, new name, table, columns)
    (
        'analyzer_testactiondata_test_id_action_id_data_r_43ee6eb5_idx',
        'ltc_tad_test_act_res_idx',
        'analyzer_testactiondata',
        '(test_id, action_id, data_resolution_id)',
    ),
    (
        'analyzer_testactionaggregatedata_test_id_action_id_73633874_idx',
        'ltc_taad_test_act_idx',
        'analyzer_testactionaggregatedata',
        '(test_id, action_id)',
    ),
    (
        'analyzer_servermonitorin_test_id_server_id_source_879cd843_idx',
        'ltc_smd_test_srv_src_res_idx',
        'analyzer_servermonitoringdata',
        '(test_id, server_id, source, data_resolution_id)',
    ),
]


def rename_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        # Non-postgres databases (e.g. SQLite test runs) created the new
        # names directly in 0001_initial.
        return
    for old, new, table, columns in RENAMES:
        schema_editor.execute(
            f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}";'
        )
        # Safety net for databases whose historical index name differs
        # (e.g. hand-managed schemas): ensure the index exists either way.
        schema_editor.execute(
            f'CREATE INDEX IF NOT EXISTS "{new}" ON "{table}" {columns};'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('analyzer', '0012_auto_20210608_1042'),
    ]

    operations = [
        migrations.RunPython(rename_indexes, migrations.RunPython.noop),
    ]
