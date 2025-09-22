<?php
require_once 'config.php';

echo "<h2>Indexação Simples MeiliSearch</h2>\n";
echo "<p>Criando índice e indexando dados...</p>\n";

try {
    // 1. Criar índice básico
    echo "<h3>1. Criando índice:</h3>\n";
    $url = MEILISEARCH_HOST . '/indexes';
    $data = json_encode(['uid' => 'coletores']);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . MEILISEARCH_KEY
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    echo "Status: $httpCode<br>\n";
    if ($httpCode === 202 || $httpCode === 201) {
        echo "✅ Índice criado<br>\n";
    } else {
        echo "⚠️ Índice pode já existir<br>\n";
    }

    // 2. Conectar MongoDB e pegar dados
    echo "<h3>2. Obtendo dados do MongoDB:</h3>\n";
    $manager = new MongoDB\Driver\Manager(MONGO_CONNECTION_STRING);

    $query = new MongoDB\Driver\Query([], ['limit' => 50]);
    $cursor = $manager->executeQuery(MONGO_DATABASE . '.coletores', $query);
    $documents = $cursor->toArray();

    echo "📄 " . count($documents) . " documentos obtidos<br>\n";

    // 3. Preparar para MeiliSearch
    echo "<h3>3. Preparando documentos:</h3>\n";
    $meilisearchDocs = [];

    foreach ($documents as $doc) {
        $variacoes = [];
        if (isset($doc->variacoes) && is_array($doc->variacoes)) {
            foreach ($doc->variacoes as $v) {
                if (isset($v->forma_original)) {
                    $variacoes[] = $v->forma_original;
                }
            }
        }

        $meilisearchDocs[] = [
            'id' => (string)$doc->_id,
            'coletor_canonico' => $doc->coletor_canonico ?? '',
            'total_registros' => $doc->total_registros ?? 0,
            'tipo_coletor' => $doc->tipo_coletor ?? '',
            'variacoes' => $variacoes
        ];
    }

    echo "✅ " . count($meilisearchDocs) . " documentos preparados<br>\n";

    // 4. Indexar
    echo "<h3>4. Indexando:</h3>\n";
    $url = MEILISEARCH_HOST . '/indexes/coletores/documents';
    $data = json_encode($meilisearchDocs);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . MEILISEARCH_KEY
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    echo "Status: $httpCode<br>\n";
    if ($httpCode === 202) {
        echo "✅ Indexação iniciada com sucesso!<br>\n";
        echo "⏳ Aguarde 5-10 segundos para completar...<br>\n";
    } else {
        echo "❌ Erro na indexação<br>\n";
        echo "Resposta: " . substr($response, 0, 200) . "<br>\n";
    }

    // 5. Teste rápido
    echo "<h3>5. Teste (após alguns segundos):</h3>\n";
    sleep(3);

    $url = MEILISEARCH_HOST . '/indexes/coletores/search';
    $data = json_encode(['q' => '', 'limit' => 3]);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . MEILISEARCH_KEY
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode === 200) {
        $result = json_decode($response, true);
        echo "✅ Busca funcionando!<br>\n";
        echo "📊 Documentos no índice: " . count($result['hits'] ?? []) . "<br>\n";

        if (!empty($result['hits'])) {
            echo "<h4>Exemplo de resultado:</h4>\n";
            $exemplo = $result['hits'][0];
            echo "Nome: " . ($exemplo['coletor_canonico'] ?? 'N/A') . "<br>\n";
            echo "Registros: " . ($exemplo['total_registros'] ?? 0) . "<br>\n";
        }
    } else {
        echo "⚠️ Busca ainda não disponível (aguarde mais um pouco)<br>\n";
    }

} catch (Exception $e) {
    echo "❌ Erro: " . $e->getMessage() . "<br>\n";
}

echo "<br><hr><br>";
echo "<strong>✅ Indexação concluída!</strong><br>\n";
echo "<a href='index.php'>🏠 Ir para página principal</a> | ";
echo "<a href='test_coletores_simples.php'>🔍 Testar novamente</a>";
?>