from PyPDF2 import PdfWriter

def merge_pdfs(pdf_list, output_path):
    merger = PdfWriter()
    for pdf in pdf_list:
        merger.append(pdf)  # Append each PDF to the merger
    with open(output_path, 'wb') as output_file:
        merger.write(output_file)
    merger.close()
    print(f"Merged {len(pdf_list)} PDFs into {output_path}")

# Example usage:
if __name__ == "__main__":
    # Replace these filenames with your actual PDF files
    input_pdfs = ["file1.pdf", "file2.pdf", "file3.pdf"]
    output_pdf = "merged_output.pdf"
    merge_pdfs(input_pdfs, output_pdf)
