<?php
require_once 'config.php';

echo "<h2>Teste Simples - Coleção Coletores</h2>\n";
echo "<p><em>Testando acesso direto à coleção 'coletores'</em></p>\n";

try {
    $manager = new MongoDB\Driver\Manager(MONGO_CONNECTION_STRING);
    echo "✅ Conectado ao MongoDB<br>\n";

    // Testar se podemos acessar a coleção coletores
    echo "<h3>1. Teste de Acesso à Coleção:</h3>\n";
    $query = new MongoDB\Driver\Query([], ['limit' => 1]);
    $cursor = $manager->executeQuery(MONGO_DATABASE . '.coletores', $query);
    $documents = $cursor->toArray();

    if (!empty($documents)) {
        echo "✅ Coleção 'coletores' acessível<br>\n";
        echo "✅ Pelo menos 1 documento encontrado<br>\n";

        echo "<h3>2. Estrutura do Documento:</h3>\n";
        $doc = $documents[0];
        echo "<strong>Campos disponíveis:</strong><br>\n";
        foreach ($doc as $field => $value) {
            $type = gettype($value);
            if (is_object($value)) {
                $type = get_class($value);
            }
            echo "- <code>$field</code> ($type)<br>\n";
        }

        echo "<h3>3. Exemplo de Documento:</h3>\n";
        echo "<pre style='background: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 400px; overflow-y: auto;'>";
        echo json_encode($doc, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
        echo "</pre>\n";

        // Testar contagem simples
        echo "<h3>4. Contagem de Documentos:</h3>\n";
        try {
            $pipeline = [['$count' => 'total']];
            $command = new MongoDB\Driver\Command([
                'aggregate' => 'coletores',
                'pipeline' => $pipeline,
                'cursor' => new stdClass,
            ]);
            $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
            $result = $cursor->toArray();
            $count = isset($result[0]->total) ? $result[0]->total : 0;
            echo "✅ Total de documentos: " . number_format($count, 0, ',', '.') . "<br>\n";
        } catch (Exception $e) {
            echo "❌ Erro ao contar: " . $e->getMessage() . "<br>\n";
        }

        // Testar busca por nome
        echo "<h3>5. Teste de Busca:</h3>\n";
        if (isset($doc->nome_canonico)) {
            $nome_exemplo = $doc->nome_canonico;
            echo "Buscando por: <strong>$nome_exemplo</strong><br>\n";

            $query = new MongoDB\Driver\Query(['nome_canonico' => $nome_exemplo], ['limit' => 1]);
            $cursor = $manager->executeQuery(MONGO_DATABASE . '.coletores', $query);
            $results = $cursor->toArray();

            if (!empty($results)) {
                echo "✅ Busca por nome funcionando<br>\n";
            } else {
                echo "❌ Busca por nome falhou<br>\n";
            }
        } else {
            echo "❌ Campo 'nome_canonico' não encontrado<br>\n";
        }

    } else {
        echo "❌ Coleção 'coletores' vazia ou inacessível<br>\n";
    }

    // Testar MeiliSearch
    echo "<h3>6. Teste MeiliSearch:</h3>\n";
    $url = MEILISEARCH_HOST . '/indexes/coletores/search';
    $data = json_encode(['q' => '', 'limit' => 1]);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . MEILISEARCH_KEY
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    echo "Status HTTP: $httpCode<br>\n";
    if ($httpCode === 200) {
        $result = json_decode($response, true);
        if (isset($result['hits'])) {
            echo "✅ MeiliSearch respondendo<br>\n";
            echo "✅ Índice 'coletores' encontrado<br>\n";
            echo "📊 Documentos no índice: " . count($result['hits']) . "<br>\n";
        } else {
            echo "❌ Resposta inesperada do MeiliSearch<br>\n";
            echo "Resposta: " . substr($response, 0, 200) . "...<br>\n";
        }
    } else {
        echo "❌ MeiliSearch erro: $httpCode<br>\n";
        echo "Resposta: " . substr($response, 0, 200) . "...<br>\n";
    }

} catch (Exception $e) {
    echo "❌ Erro: " . $e->getMessage() . "<br>\n";
}

echo "<br><hr><br>";
echo "<a href='index.php'>← Voltar para a página principal</a> | ";
echo "<a href='test_conexao.php'>Teste de conexão</a>";
?>