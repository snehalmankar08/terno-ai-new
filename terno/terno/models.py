from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group


class DataSource(models.Model):
    class DBType(models.TextChoices):
        default = "generic", _("Generic")
        Oracle = "oracle", _("Oracle")
        MSSQL = "mysql", _("MySQL")
        postgres = "postgres", _("Postgres")
    type = models.CharField(max_length=20,
                            choices=DBType,
                            default=DBType.default
                            )
    connection_str = models.CharField(max_length=300)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.connection_str


class Table(models.Model):
    """Model to represent a table in the data source."""
    name = models.CharField(max_length=255)
    pub_name = models.CharField(max_length=255, null=True, blank=True)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.data_source} - {self.name}"

    def get_table_name(self):
        return self.pub_name if self.pub_name else self.name


class TableColumn(models.Model):
    """Model to represent a column in a table."""
    name = models.CharField(max_length=255)
    pub_name = models.CharField(max_length=255, null=True, blank=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    data_type = models.CharField(max_length=50, blank=True)  # Optional field for data type

    def __str__(self):
        return f"{self.table} - {self.name}"

    def get_column_name(self):
        return self.pub_name if self.pub_name else self.name


class TableSelector(models.Model):
    """Model for user to select tables."""
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    tables = models.ManyToManyField(Table, blank=True)

    def __str__(self):
        selected_tables = ", ".join([str(table) for table in self.tables.all()])
        return f"Selected tables from {self.data_source}: {selected_tables}"


class GroupTableSelector(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    tables = models.ManyToManyField(Table, blank=True,
                                    related_name='include_tables')
    exclude_tables = models.ManyToManyField(Table, blank=True,
                                            related_name='exclude_tables')

    def __str__(self) -> str:
        return f'{self.group.name}'

    def get_pub_table(self):
        tables_items = self.tables.all()
        exclude_tables_items = self.exclude_tables.all()
        diff = tables_items.difference(exclude_tables_items)
        return diff


class GroupColumnSelector(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    columns = models.ManyToManyField(TableColumn, blank=True,
                                     related_name='include_columns')
    exclude_columns = models.ManyToManyField(TableColumn, blank=True,
                                             related_name='exclude_columns')

    def __str__(self) -> str:
        return f'{self.group.name}'

    def get_pub_column(self):
        columns_items = self.columns.all()
        exclude_columns_items = self.exclude_columns.all()
        diff = columns_items.difference(exclude_columns_items)
        return diff


class GroupTableRowFilterSelector(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    filter_str = models.CharField(max_length=300)
