<?php
require_once 'config.php';

echo "<h2>Indexação MeiliSearch - Coletores</h2>\n";

try {
    // Conectar ao MongoDB
    $manager = new MongoDB\Driver\Manager(MONGO_CONNECTION_STRING);
    echo "✅ Conectado ao MongoDB<br>\n";

    // 1. Criar índice no MeiliSearch
    echo "<h3>1. Criando índice no MeiliSearch:</h3>\n";
    $url = MEILISEARCH_HOST . '/indexes';
    $data = json_encode([
        'uid' => 'coletores',
        'primaryKey' => '_id'
    ]);

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

    if ($httpCode === 202 || $httpCode === 200) {
        echo "✅ Índice criado/já existe<br>\n";
    } else {
        echo "⚠️ Status: $httpCode - " . substr($response, 0, 100) . "<br>\n";
    }

    // 2. Configurar campos pesquisáveis
    echo "<h3>2. Configurando campos pesquisáveis:</h3>\n";
    $url = MEILISEARCH_HOST . '/indexes/coletores/settings/searchable-attributes';
    $data = json_encode(['coletor_canonico', 'variacoes']);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Authorization: Bearer ' . MEILISEARCH_KEY
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLOPT_HTTP_CODE);
    curl_close($ch);

    if ($httpCode === 202) {
        echo "✅ Campos pesquisáveis configurados<br>\n";
    } else {
        echo "⚠️ Status: $httpCode<br>\n";
    }

    // 3. Buscar amostra de documentos do MongoDB
    echo "<h3>3. Preparando dados para indexação:</h3>\n";
    $query = new MongoDB\Driver\Query([], ['limit' => 100]); // Começar com 100 documentos
    $cursor = $manager->executeQuery(MONGO_DATABASE . '.coletores', $query);
    $documents = $cursor->toArray();

    echo "📄 " . count($documents) . " documentos obtidos do MongoDB<br>\n";

    // 4. Preparar documentos para MeiliSearch
    $meilisearchDocs = [];
    foreach ($documents as $doc) {
        $meilisearchDoc = [
            '_id' => (string)$doc->_id,
            'coletor_canonico' => $doc->coletor_canonico ?? '',
            'total_registros' => $doc->total_registros ?? 0,
            'tipo_coletor' => $doc->tipo_coletor ?? '',
        ];

        // Extrair variações como array de strings
        if (isset($doc->variacoes) && is_array($doc->variacoes)) {
            $variacoes = [];
            foreach ($doc->variacoes as $variacao) {
                if (isset($variacao->forma_original)) {
                    $variacoes[] = $variacao->forma_original;
                }
            }
            $meilisearchDoc['variacoes'] = $variacoes;
        }

        $meilisearchDocs[] = $meilisearchDoc;
    }

    // 5. Indexar no MeiliSearch
    echo "<h3>4. Indexando documentos:</h3>\n";
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

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode === 202) {
        $result = json_decode($response, true);
        echo "✅ Indexação iniciada<br>\n";
        echo "📋 Task ID: " . ($result['taskUid'] ?? 'N/A') . "<br>\n";
        echo "⏳ Aguarde alguns segundos para a indexação completar<br>\n";
    } else {
        echo "❌ Erro na indexação: $httpCode<br>\n";
        echo "Resposta: " . substr($response, 0, 200) . "<br>\n";
    }

    // 6. Teste de busca
    echo "<h3>5. Teste de busca (aguarde 10 segundos):</h3>\n";
    echo "<script>setTimeout(function(){ location.reload(); }, 10000);</script>\n";

    sleep(2); // Aguardar um pouco

    $url = MEILISEARCH_HOST . '/indexes/coletores/search';
    $data = json_encode(['q' => '', 'limit' => 5]);

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

    if ($httpCode === 200) {
        $result = json_decode($response, true);
        echo "✅ Busca funcionando<br>\n";
        echo "📊 Documentos encontrados: " . count($result['hits'] ?? []) . "<br>\n";
    } else {
        echo "⚠️ Busca ainda não disponível (Status: $httpCode)<br>\n";
    }

} catch (Exception $e) {
    echo "❌ Erro: " . $e->getMessage() . "<br>\n";
}

echo "<br><hr><br>";
echo "<a href='index.php'>← Voltar para a página principal</a> | ";
echo "<a href='test_coletores_simples.php'>Testar novamente</a>";
?>