from flask import Flask, request, send_file
from flask_cors import CORS
import fitz  # PyMuPDF
import tempfile, os, zipfile, shutil

app = Flask(__name__)
CORS(app)  # in production restrict origin to your GitHub Pages domain

@app.route('/api/convert', methods=['POST'])
def convert():
    files = request.files.getlist('files')
    if not files:
        return 'No files uploaded', 400

    # create a temp folder for this request
    work_dir = tempfile.mkdtemp(prefix='pdf2png_')
    zip_path = os.path.join(work_dir, 'converted_pngs.zip')
    zf = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)

    try:
        for upload in files:
            original_name = upload.filename or 'file.pdf'
            base = os.path.splitext(original_name)[0]
            pdf_path = os.path.join(work_dir, original_name)
            upload.save(pdf_path)

            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc, start=1):
                # Prefer TrimBox, then CropBox, then full page
                rect = None
                if hasattr(page, 'trimbox') and page.trimbox:
                    rect = page.trimbox
                elif hasattr(page, 'cropbox') and page.cropbox:
                    rect = page.cropbox
                else:
                    rect = page.rect

                # Render at a scaling (2x) for quality; adjust as needed
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat, clip=rect, alpha=False)

                out_name = f"{base}_p{i:03d}.png"
                out_path = os.path.join(work_dir, out_name)
                pix.save(out_path)
                zf.write(out_path, arcname=out_name)

            doc.close()
            # remove the uploaded pdf file
            os.remove(pdf_path)

        zf.close()
        return send_file(zip_path, mimetype='application/zip', as_attachment=True, download_name='converted_pngs.zip')
    finally:
        # cleanup after sending file (the file will be kept until response finishes)
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
