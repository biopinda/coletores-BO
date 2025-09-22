<?php
echo "<h1>Teste PHP</h1>";
echo "<p>Data/Hora: " . date('Y-m-d H:i:s') . "</p>";
echo "<p>Versão PHP: " . phpversion() . "</p>";

if (extension_loaded('mongodb')) {
    echo "<p style='color: green;'>✅ Extensão MongoDB carregada</p>";
} else {
    echo "<p style='color: red;'>❌ Extensão MongoDB não carregada</p>";
}

phpinfo();
?>