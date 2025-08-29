# PDF-Form-Filler-and-Merger-

This project demonstrates how to fill PDF forms programmatically and
with a simple GUI. It uses **PyPDF2** and **ReportLab** for processing
and flattening form fields.

## Files

-   **`simple_pdf_filler.py`**\
    A command-line tool to fill out PDF form fields and flatten them so
    the values are always visible (even in PDF viewers that don't show
    form fields).
    -   Supports text fields, checkboxes, radio buttons, and
        dropdown/list fields.\

    -   Example usage:

        ``` bash
        python simple_pdf_filler.py input.pdf output.pdf
        ```

        Edit the `DATA` dictionary inside the script with your values.
-   **`pdf_form_gui.py`**\
    A graphical interface for filling PDF forms without editing the
    script.
    -   Lets users enter data in text fields and tick checkboxes from a
        simple window.\
    -   Calls the backend functions in `simple_pdf_filler.py` to
        generate the final filled PDF.
-   **`your_form.pdf`**\
    A sample fillable PDF containing common field types (text fields,
    checkboxes, combo boxes, list boxes). Use this file for testing.

## Installation

1.  Clone or download this project.\

2.  Install the required Python libraries:

    ``` bash
    pip install PyPDF2 reportlab
    ```

## Usage

### Command-line

``` bash
python simple_pdf_filler.py your_form.pdf filled_output.pdf
```

Values are taken from the `DATA` dictionary defined inside the script.

### GUI

``` bash
python pdf_form_gui.py
```

Enter your details in the GUI and export the filled PDF.

## Features

-   Fill text fields (e.g., name, address).\
-   Check/uncheck checkboxes (e.g., languages).\
-   Select single or multiple values from dropdowns/lists.\
-   Flatten fields so all values are visible in any PDF reader.

## Example Workflow

1.  Open **your_form.pdf** to see the blank form.\
2.  Run either the command-line tool or the GUI to enter your details.\
3.  Export the final filled PDF, where all fields are flattened and
    visible.
