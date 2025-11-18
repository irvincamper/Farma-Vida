// app/static/js/pdf_generator.js

/**
 * Función para generar un PDF a partir de un elemento HTML.
 * @param {string} elementId - El ID del elemento HTML que se convertirá en PDF.
 * @param {string} fileName - El nombre del archivo PDF que se descargará.
 */
function generatePdf(elementId, fileName = 'receta.pdf') {
    // 1. Obtenemos el elemento del DOM que queremos convertir.
    const element = document.getElementById(elementId);

    // Si el elemento no existe, mostramos un error en la consola y salimos.
    if (!element) {
        console.error(`Error: Elemento con ID "${elementId}" no fue encontrado.`);
        alert("Hubo un error al generar el PDF. El contenido no se encontró.");
        return;
    }

    // 2. Opciones de configuración para la generación del PDF.
    const opt = {
      margin:       1, // Margen en la unidad de jsPDF (pulgadas por defecto)
      filename:     fileName,
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true }, // 'scale' mejora la resolución
      jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
    };

    // 3. Mostramos un pequeño feedback al usuario
    alert("Generando su PDF, la descarga comenzará en un momento...");

    // 4. Llamamos a la librería html2pdf para generar y descargar el archivo.
    html2pdf().from(element).set(opt).save();
}