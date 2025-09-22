<?php
// Script para testar a conexão com MongoDB - VERSÃO ATUALIZADA
// Timestamp: <?php echo date('Y-m-d H:i:s'); ?>

// Limpar qualquer cache de opcodes
if (function_exists('opcache_reset')) {
    opcache_reset();
}

require_once 'config.php';

echo "<h2>Teste de Conexão - Biodiversidade Online (NOVA VERSÃO)</h2>\n";
echo "<p><em>Última atualização: " . date('Y-m-d H:i:s') . "</em></p>\n";

// 1. Verificar se arquivo config.php existe e está carregado
echo "<h3>1. Configurações:</h3>\n";
if (defined('MONGO_HOST')) {
    echo "✅ MONGO_HOST: " . MONGO_HOST . "\n<br>";
} else {
    echo "❌ MONGO_HOST não definido\n<br>";
}

if (defined('MONGO_PORT')) {
    echo "✅ MONGO_PORT: " . MONGO_PORT . "\n<br>";
} else {
    echo "❌ MONGO_PORT não definido\n<br>";
}

if (defined('MONGO_DATABASE')) {
    echo "✅ MONGO_DATABASE: " . MONGO_DATABASE . "\n<br>";
} else {
    echo "❌ MONGO_DATABASE não definido\n<br>";
}

if (defined('MONGO_COLLECTION')) {
    echo "✅ MONGO_COLLECTION: " . MONGO_COLLECTION . "\n<br>";
} else {
    echo "❌ MONGO_COLLECTION não definido\n<br>";
}

if (defined('MONGO_CONNECTION_STRING')) {
    echo "✅ MONGO_CONNECTION_STRING: DEFINIDA\n<br>";
} else {
    echo "❌ MONGO_CONNECTION_STRING não definida\n<br>";
}

// 2. Verificar extensão MongoDB
echo "<h3>2. Extensões PHP:</h3>\n";
if (extension_loaded('mongodb')) {
    echo "✅ Extensão MongoDB carregada\n<br>";
} else {
    echo "❌ Extensão MongoDB NÃO carregada\n<br>";
    echo "Execute: <code>composer require mongodb/mongodb</code>\n<br>";
}

// 3. Testar conexão
echo "<h3>3. Teste de Conexão:</h3>\n";
try {
    if (!extension_loaded('mongodb')) {
        throw new Exception('Extensão MongoDB não está disponível');
    }

    // Usar string de conexão completa se disponível
    if (defined('MONGO_CONNECTION_STRING')) {
        $connectionString = MONGO_CONNECTION_STRING;
        echo "✅ Usando string de conexão completa definida no config\n<br>";
        echo "String de conexão: " . $connectionString . "\n<br>";
    } else {
        echo "❌ String de conexão completa não encontrada, construindo...\n<br>";
        // Construir string de conexão com autenticação se disponível
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
            echo "String de conexão: mongodb://[usuário]:[senha]@" . MONGO_HOST . ":" . MONGO_PORT . "/" . MONGO_DATABASE . "?authSource=" . $authSource . "\n<br>";
        } else {
            $connectionString = "mongodb://" . MONGO_HOST . ":" . MONGO_PORT;
            echo "String de conexão: " . $connectionString . "\n<br>";
        }
    }

    $manager = new MongoDB\Driver\Manager($connectionString);

    // Testar conexão com query simples (compatível com read-only)
    $query = new MongoDB\Driver\Query([], ['limit' => 1]);
    $cursor = $manager->executeQuery(MONGO_DATABASE . '.' . MONGO_COLLECTION, $query);

    echo "✅ Conexão com MongoDB estabelecida com sucesso!\n<br>";

    // 4. Verificar se a base de dados existe
    echo "<h3>4. Verificação da Base de Dados:</h3>\n";

    // Contar documentos usando aggregate (compatível com read-only)
    $pipeline = [['$count' => 'total']];
    $command = new MongoDB\Driver\Command([
        'aggregate' => MONGO_COLLECTION,
        'pipeline' => $pipeline,
        'cursor' => new stdClass,
    ]);

    try {
        $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
        $result = $cursor->toArray();
        $count = isset($result[0]->total) ? $result[0]->total : 0;

        echo "✅ Coleção '" . MONGO_COLLECTION . "' acessível\n<br>";
        echo "📊 Total de documentos na coleção: " . number_format($count, 0, ',', '.') . "\n<br>";

        if ($count > 0) {
            // Buscar um documento de exemplo
            $query = new MongoDB\Driver\Query([], ['limit' => 1]);
            $cursor = $manager->executeQuery(MONGO_DATABASE . '.' . MONGO_COLLECTION, $query);
            $documents = $cursor->toArray();

            if (!empty($documents)) {
                echo "<h3>5. Exemplo de Documento:</h3>\n";
                echo "<pre>" . json_encode($documents[0], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "</pre>\n";
            }
        }
    } catch (Exception $e) {
        echo "❌ Erro ao verificar base de dados: " . $e->getMessage() . "\n<br>";
    }

} catch (Exception $e) {
    echo "❌ Erro na conexão: " . $e->getMessage() . "\n<br>";
}

// 5. Verificar MeiliSearch
echo "<h3>6. Teste MeiliSearch:</h3>\n";
if (defined('MEILISEARCH_HOST') && defined('MEILISEARCH_KEY')) {
    echo "Host MeiliSearch: " . MEILISEARCH_HOST . "\n<br>";

    $url = MEILISEARCH_HOST . '/health';
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Authorization: Bearer ' . MEILISEARCH_KEY
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($response !== false && $httpCode === 200) {
        echo "✅ MeiliSearch respondendo (status: " . $httpCode . ")\n<br>";
    } else {
        echo "❌ MeiliSearch não respondeu (status: " . $httpCode . ")\n<br>";
    }
} else {
    echo "❌ Configurações do MeiliSearch não encontradas\n<br>";
}

echo "<br><hr><br>";
echo "<a href='index.php'>← Voltar para a página principal</a> | ";
echo "<a href='test_conexao.php'>Testar versão antiga</a>";
?>