<?php
// Debug das configurações
require_once 'config.php';

echo "<h2>Debug - Configurações MongoDB</h2>\n";

echo "<h3>Constantes definidas:</h3>\n";
echo "MONGO_HOST: " . (defined('MONGO_HOST') ? MONGO_HOST : 'INDEFINIDO') . "<br>\n";
echo "MONGO_PORT: " . (defined('MONGO_PORT') ? MONGO_PORT : 'INDEFINIDO') . "<br>\n";
echo "MONGO_DATABASE: " . (defined('MONGO_DATABASE') ? MONGO_DATABASE : 'INDEFINIDO') . "<br>\n";
echo "MONGO_COLLECTION: " . (defined('MONGO_COLLECTION') ? MONGO_COLLECTION : 'INDEFINIDO') . "<br>\n";
echo "MONGO_USERNAME: " . (defined('MONGO_USERNAME') ? MONGO_USERNAME : 'INDEFINIDO') . "<br>\n";
echo "MONGO_PASSWORD: " . (defined('MONGO_PASSWORD') ? '[SENHA DEFINIDA]' : 'INDEFINIDO') . "<br>\n";
echo "MONGO_AUTH_SOURCE: " . (defined('MONGO_AUTH_SOURCE') ? MONGO_AUTH_SOURCE : 'INDEFINIDO') . "<br>\n";

echo "<h3>String de conexão construída:</h3>\n";
if (defined('MONGO_USERNAME') && defined('MONGO_PASSWORD')) {
    $authSource = defined('MONGO_AUTH_SOURCE') ? MONGO_AUTH_SOURCE : MONGO_DATABASE;
    $connectionString = sprintf(
        "mongodb://%s:%s@%s:%d/%s?authSource=%s",
        urlencode(MONGO_USERNAME),
        urlencode(MONGO_PASSWORD),
        MONGO_HOST,
        MONGO_PORT,
        MONGO_DATABASE,
        $authSource
    );
    echo "String completa: <code>" . $connectionString . "</code><br>\n";
    echo "String para exibição: <code>mongodb://[usuario]:[senha]@" . MONGO_HOST . ":" . MONGO_PORT . "/" . MONGO_DATABASE . "?authSource=" . $authSource . "</code><br>\n";
} else {
    echo "❌ Credenciais não definidas<br>\n";
}

echo "<h3>Teste de conexão:</h3>\n";
try {
    if (!extension_loaded('mongodb')) {
        throw new Exception('Extensão MongoDB não carregada');
    }

    $manager = new MongoDB\Driver\Manager($connectionString);
    $query = new MongoDB\Driver\Query([], ['limit' => 1]);
    $cursor = $manager->executeQuery(MONGO_DATABASE . '.' . MONGO_COLLECTION, $query);

    echo "✅ Conexão funcionando!<br>\n";
} catch (Exception $e) {
    echo "❌ Erro: " . $e->getMessage() . "<br>\n";
}
?>