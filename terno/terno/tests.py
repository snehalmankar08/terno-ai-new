from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User, Group
import terno.models as models
import terno.utils as utils
import terno.llm as llms
from terno.pipeline.pipeline import Pipeline
from terno.pipeline.step import Step


class BaseTestCase(TestCase):
    def create_user(self):
        return User.objects.create_user(username='testuser', password='12345')

    def create_datasource(self, display_name='test_db'):
        datasource = models.DataSource.objects.create(
            display_name=display_name, type='default',
            connection_str='sqlite:///../chinook.db',
            enabled=True
        )
        return datasource

    def create_mdb(self, ds_display_name='test_db', roles='sales'):
        ds = self.create_datasource()
        roles = Group.objects.create(name=roles)

        # Setting private tables for all
        global_private_table_names = ['Invoice', 'Customer', 'Employee']
        global_private_tables = models.Table.objects.filter(
            name__in=global_private_table_names)
        private_table_selector = models.PrivateTableSelector.objects.create(
            data_source=ds)
        for table in global_private_tables:
            private_table_selector.tables.add(table)

        # Setting private tables for roles
        group_allowed_table_names = ['Invoice']
        group_allowed_tables = models.Table.objects.filter(
            name__in=group_allowed_table_names)
        group_table_selector = models.GroupTableSelector.objects.create(
            group=roles)
        for table in group_allowed_tables:
            group_table_selector.tables.add(table)

        # Setting private columns for all
        global_private_column_names = ['Invoice', 'Customer', 'Employee']
        global_private_tables = models.TableColumn.objects.filter(
            name__in=global_private_column_names)
        private_table_selector = models.PrivateTableSelector.objects.create(
            data_source=ds)
        for table in global_private_tables:
            private_table_selector.tables.add(table)

        # Setting private columns for roles
        group_allowed_column_names = ['Invoice']
        group_allowed_tables = models.TableColumn.objects.filter(
            name__in=group_allowed_column_names)
        group_table_selector = models.GroupTableSelector.objects.create(
            group=roles)
        for table in group_allowed_tables:
            group_table_selector.tables.add(table)

        mdb = utils.prepare_mdb(ds, [roles])
        return mdb


class DBEngineTestCase(TestCase):
    def setUp(self):
        self.connection_string = "sqlite:///../chinook.db"
        self.bigquery_connection_string = "bigquery://project/dataset"
        self.credentials_info = {
            "type": "service_account",
            "project_id": "your-project-id"
        }

    def test_create_db_engine(self):
        engine = utils.create_db_engine('sqlite', self.connection_string)
        with engine.connect():
            self.assertEqual(engine.dialect.name, 'sqlite')
            self.assertEqual(str(engine.dialect.server_version_info), '(3, 46, 1)')

    @patch('terno.utils.sqlalchemy.create_engine')
    def test_create_db_engine_bigquery(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        engine = utils.create_db_engine('bigquery',
                                        self.bigquery_connection_string,
                                        credentials_info=self.credentials_info)

        mock_create_engine.assert_called_once_with(
            self.bigquery_connection_string,
            credentials_info=self.credentials_info)
        self.assertEqual(engine, mock_engine)

    @patch('terno.utils.sqlalchemy.create_engine')
    def test_create_db_engine_bigquery_missing_credentials(self,
                                                           mock_create_engine):
        with self.assertRaises(ValueError) as context:
            utils.create_db_engine('bigquery', self.bigquery_connection_string)

        self.assertEqual(str(context.exception),
                         "BigQuery requires credentials_info")
        mock_create_engine.assert_not_called()


class DataSourceTestCase(BaseTestCase):
    def setUp(self) -> None:
        self.datasource = super().create_datasource()

    def test_datasource_created(self):
        self.assertEqual(str(self.datasource), 'test_db')

    def test_tables_are_created(self):
        tables = models.Table.objects.all()
        self.assertEqual(tables.exists(), True)
        self.assertEqual(tables.first().public_name, tables.first().name)

    def test_columns_are_created(self):
        table_columns = models.TableColumn.objects.all()
        self.assertEqual(table_columns.exists(), True)
        self.assertEqual(table_columns.first().public_name,
                         table_columns.first().name)


class FilterTestCase(BaseTestCase):
    def setUp(self) -> None:
        self.datasource = super().create_datasource()

    def test_user_can_access_all_tables(self):
        utils.get_admin_config_object(self.datasource, roles=[])


class MDBTestCase(BaseTestCase):
    def setUp(self) -> None:
        self.mdb = super().create_mdb()

    def test_allowed_tables(self):
        mdb = self.mdb
        self.assertEqual(list(mdb.tables.keys()),
                         ['Album', 'Artist', 'Genre', 'Invoice',
                          'InvoiceLine', 'MediaType', 'Playlist',
                          'PlaylistTrack', 'Track', 'User'])

    def test_allowed_columns(self):
        mdb = self.mdb
        for table in mdb.tables.values():
            # print(table.columns)
            pass

    def test_generated_schema(self):
        schema = self.mdb.generate_schema()
        self.assertIn('CREATE TABLE [Album]', schema)
        self.assertIn('[BillingPostalCode] NVARCHAR(10),', schema)
        self.assertIn('FOREIGN KEY ([PlaylistId]) REFERENCES [Playlist] ([PlaylistId])', schema)


class LLMTestCase(BaseTestCase):
    def setUp(self) -> None:
        self.fake_llm = llms.FakeLLM(api_key="test_key")
        self.openai_llm = llms.OpenAILLM(api_key="")

    def test_fake_llm(self):
        response = self.fake_llm.get_response('messages')
        self.assertEqual(response, "SELECT 1")


class LLMResponseTestCase(BaseTestCase):
    def setUp(self):
        self.user = super().create_user()
        self.datasource = super().create_datasource()
        self.user_query = "Show me all albums"
        self.db_schema = "CREATE TABLE Album (AlbumId INTEGER, Title NVARCHAR(160), ArtistId INTEGER)"

    @patch('terno.utils.LLMFactory.create_llm')
    @patch('terno.utils.create_pipeline')
    @patch('terno.utils.get_response_from_pipeline')
    def test_llm_response_success(self, mock_get_response,
                                  mock_create_pipeline, mock_create_llm):
        mock_llm = MagicMock(spec=llms.BaseLLM)
        mock_create_llm.return_value = mock_llm

        mock_pipeline = MagicMock(spec=Pipeline)
        mock_create_pipeline.return_value = mock_pipeline

        mock_get_response.return_value = [["SELECT * FROM Album"]]

        response = utils.llm_response(self.user, self.user_query,
                                      self.db_schema, self.datasource)

        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['generated_sql'], "SELECT * FROM Album")
        mock_create_llm.assert_called_once()
        mock_create_pipeline.assert_called_once_with(
            mock_llm, 'one_step_pipeline', self.user,
            self.db_schema, self.datasource, self.user_query)
        mock_get_response.assert_called_once_with(mock_pipeline)

    @patch('terno.utils.LLMFactory.create_llm')
    def test_llm_response_error(self, mock_create_llm):
        mock_create_llm.side_effect = Exception("LLM Error")

        response = utils.llm_response(self.user, self.user_query, self.db_schema, self.datasource)

        self.assertEqual(response['status'], 'error')
        self.assertIn('LLM Error', response['error'])


class CreatePipelineTestCase(BaseTestCase):
    def setUp(self):
        self.user = super().create_user()
        self.datasource = super().create_datasource()
        self.user_query = "Show me all albums"
        self.db_schema = "CREATE TABLE Album (AlbumId INTEGER, Title NVARCHAR(160), ArtistId INTEGER)"
        self.llm = MagicMock(spec=llms.BaseLLM)

    @patch('terno.utils.query_generation')
    def test_create_pipeline_one_step(self, mock_query_generation):
        mock_query_generation.query_generation_system_prompt = "System prompt"
        mock_query_generation.query_generation_ai_prompt = "AI prompt"
        mock_query_generation.query_generation_human_prompt = "Human prompt"

        self.llm.create_message_for_llm.return_value = ["Mocked message"]

        pipeline = utils.create_pipeline(self.llm, 'one_step_pipeline',
                                         self.user, self.db_schema,
                                         self.datasource, self.user_query)

        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(len(pipeline._steps), 1)
        self.assertIsInstance(pipeline._steps[0], Step)

        self.llm.create_message_for_llm.assert_called_once_with(
            "System prompt",
            "AI prompt",
            "Human prompt"
        )

        self.assertEqual(models.PromptLog.objects.count(), 1)
        prompt_log = models.PromptLog.objects.first()
        self.assertEqual(prompt_log.user, self.user)
        self.assertEqual(prompt_log.llm_prompt, "['Mocked message']")

    def test_create_pipeline_invalid_name(self):
        with self.assertRaises(Exception) as context:
            utils.create_pipeline(self.llm, 'invalid_pipeline',
                                  self.user, self.db_schema,
                                  self.datasource, self.user_query)

        self.assertEqual(str(context.exception), "Invalid Pipeline Name")


class GenerateExecuteNativeSQLTestCase(BaseTestCase):
    def setUp(self) -> None:
        self.mdb = super().create_mdb()

    def test_generate_native_sql(self):
        response = utils.generate_native_sql(self.mdb, 'SELECT * from Album;')
        expected_sql = 'SELECT * FROM (SELECT AlbumId AS AlbumId, Title AS Title, ArtistId AS ArtistId FROM Album) AS Album'

        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['native_sql'],
                         expected_sql)

    def test_generate_native_sql_error(self):
        response = utils.generate_native_sql(self.mdb, 'SELECT * from InvalidTable;')

        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['error'],
                         "('No such table found.', 'InvalidTable')")

    def test_execute_native_sql(self):
        datasource = models.DataSource.objects.get(display_name='test_db')
        native_sql = 'SELECT * FROM (SELECT AlbumId AS AlbumId, Title AS Title, ArtistId AS ArtistId FROM Album);'
        result = utils.execute_native_sql(datasource, native_sql, 1, 25)

        self.assertListEqual(list(result['table_data'].keys()),
                             ['columns', 'total_pages', 'row_count', 'page', 'data'])
        self.assertEqual(result['table_data']['columns'],
                         ['AlbumId', 'Title', 'ArtistId'])
        self.assertEqual(result['table_data']['total_pages'], 13)
        self.assertEqual(result['table_data']['row_count'], 347)
        self.assertEqual(result['table_data']['page'], 1)


class SubstituteTestCase(BaseTestCase):
    def setUp(self) -> None:
        self.mdb = super().create_mdb()

    def test_extract_limit_from_query(self):
        datasource = models.DataSource.objects.get(display_name='test_db')
        template_str = "{{db_schema}} {{dialect_name}} {{dialect_version}}"
        context_dict = {
            'db_schema': self.mdb.generate_schema(),
            'dialect_name': datasource.dialect_name,
            'dialect_version': datasource.dialect_version,
        }

        response = utils.substitute_variables(template_str, context_dict)
        expected_response = f"{context_dict['db_schema']} {context_dict['dialect_name']} {context_dict['dialect_version']}"

        self.assertEqual(response, expected_response)
