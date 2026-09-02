# Contribuir

Se agradecen los reportes de errores y los pull requests concretos.

Antes de enviar un cambio:

1. Ejecuta `python -m unittest discover -s tests -p "test_*.py"` desde el entorno virtual del proyecto.
2. Mantén las comprobaciones de firmas y seguridad en modo fail-closed: una revisión desconocida del juego o una estructura de diálogo no reconocida debe desactivar la modificación o volver al español, nunca parchear una dirección sin verificar.
3. Documenta cualquier nueva dirección de runtime indicando la revisión del juego, la evidencia y un método reproducible para obtenerla.

Los reportes deberían incluir la versión de PPSSPP, la edición/hash de la ISO cuando sea relevante, el hash de la compilación del plugin, el fragmento de log correspondiente, pasos de reproducción y una captura de pantalla.
