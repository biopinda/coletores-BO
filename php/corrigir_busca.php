<?php
require_once 'config.php';

echo "<h2>Corrigir Busca MeiliSearch</h2>\n";
echo "<p>Reindexando com campos de busca corretos...</p>\n";

try {
    // 1. Deletar índice atual
    echo "<h3>1. Deletando índice atual:</h3>\n";
    $url = MEILISEARCH_HOST . '/indexes/coletores';

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Authorization: Bearer ' . MEILISEARCH_KEY
    ]);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    echo "Status: $httpCode<br>\n";

    // 2. Criar novo índice
    echo "<h3>2. Criando novo índice:</h3>\n";
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

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    echo "Status: $httpCode<br>\n";
    sleep(2);

    // 3. Configurar campos pesquisáveis
    echo "<h3>3. Configurando campos de busca:</h3>\n";
    $url = MEILISEARCH_HOST . '/indexes/coletores/settings/searchable-attributes';
    $data = json_encode([
        'coletor_canonico',
        'sobrenome_normalizado',
        'variacoes_texto',
        'tipo_coletor'
    ]);

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
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    echo "Status: $httpCode<br>\n";
    sleep(2);

    // 4. Conectar MongoDB e pegar dados
    echo "<h3>4. Obtendo dados do MongoDB:</h3>\n";
    $manager = new MongoDB\Driver\Manager(MONGO_CONNECTION_STRING);

    $query = new MongoDB\Driver\Query([], ['limit' => 500]);
    $cursor = $manager->executeQuery(MONGO_DATABASE . '.coletores', $query);
    $documents = $cursor->toArray();

    echo "📄 " . count($documents) . " documentos obtidos<br>\n";

    // 5. Preparar para MeiliSearch com busca melhorada
    echo "<h3>5. Preparando documentos com campos de busca:</h3>\n";
    $meilisearchDocs = [];

    foreach ($documents as $doc) {
        $variacoes = [];
        $variacoesTexto = '';

        if (isset($doc->variacoes) && is_array($doc->variacoes)) {
            foreach ($doc->variacoes as $v) {
                if (isset($v->forma_original)) {
                    $variacoes[] = $v->forma_original;
                    $variacoesTexto .= ' ' . $v->forma_original;
                }
            }
        }

        $meilisearchDocs[] = [
            'id' => (string)$doc->_id,
            'coletor_canonico' => $doc->coletor_canonico ?? '',
            'sobrenome_normalizado' => $doc->sobrenome_normalizado ?? '',
            'total_registros' => $doc->total_registros ?? 0,
            'tipo_coletor' => $doc->tipo_coletor ?? '',
            'variacoes' => $variacoes,
            'variacoes_texto' => trim($variacoesTexto), // Campo texto para busca
            'kingdom' => $doc->kingdom ?? [],
            'confianca_canonicalizacao' => $doc->confianca_canonicalizacao ?? 0,
            'confianca_tipo_coletor' => $doc->confianca_tipo_coletor ?? 0
        ];
    }

    echo "✅ " . count($meilisearchDocs) . " documentos preparados<br>\n";

    // 6. Indexar
    echo "<h3>6. Indexando:</h3>\n";
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
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    echo "Status: $httpCode<br>\n";
    if ($httpCode === 202) {
        echo "✅ Indexação iniciada com sucesso!<br>\n";
        echo "⏳ Aguarde alguns segundos para completar...<br>\n";
    } else {
        echo "❌ Erro na indexação<br>\n";
        echo "Resposta: " . substr($response, 0, 200) . "<br>\n";
    }

    // 7. Teste da busca
    echo "<h3>7. Testando busca:</h3>\n";
    sleep(5);

    $termosTeste = ['Silva', 'Santos', 'Amanda', 'pessoa'];

    foreach ($termosTeste as $termo) {
        echo "<strong>Testando: '$termo'</strong><br>\n";

        $url = MEILISEARCH_HOST . '/indexes/coletores/search';
        $data = json_encode([
            'q' => $termo,
            'limit' => 3,
            'attributesToHighlight' => ['coletor_canonico', 'sobrenome_normalizado', 'variacoes_texto']
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

        if ($httpCode === 200) {
            $result = json_decode($response, true);
            echo "✅ " . count($result['hits'] ?? []) . " resultados encontrados<br>\n";

            if (!empty($result['hits'])) {
                foreach ($result['hits'] as $hit) {
                    echo "- " . ($hit['coletor_canonico'] ?? 'N/A') . " (" . ($hit['total_registros'] ?? 0) . " registros)<br>\n";
                }
            }
        } else {
            echo "❌ Erro na busca: $httpCode<br>\n";
        }
        echo "<br>\n";
    }

} catch (Exception $e) {
    echo "❌ Erro: " . $e->getMessage() . "<br>\n";
}

echo "<br><hr><br>";
echo "<strong>✅ Correção da busca concluída!</strong><br>\n";
echo "<a href='index.php'>🏠 Ir para página principal</a>";
?>