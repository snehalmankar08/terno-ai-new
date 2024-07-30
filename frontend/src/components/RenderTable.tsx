import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/Table";

interface RenderTableProps {
  columns: string[];
  data: Record<string, string | number>[];
}

const RenderTable: React.FC<RenderTableProps> = ({ columns, data }) => {
  return (
    <Table className="border border-slate-500">
      <TableCaption>A list of your result.</TableCaption>
      <TableHeader>
          {columns.map((column) => (
            <TableHead
              key={column}
              className="border border-slate-500"
            >
              {column}
            </TableHead>
          ))}
      </TableHeader>
      <TableBody>
        {data.map((row, rowIndex) => (
          <TableRow key={rowIndex}>
            {columns.map((column) => (
              <TableCell
                key={`${rowIndex}-${column}`}
                className="border"
              >
                {row[column]}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default RenderTable;
