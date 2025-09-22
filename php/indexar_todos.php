<?php
require_once 'config.php';

echo "<h2>Indexação Completa MeiliSearch</h2>\n";
echo "<p>Indexando todos os 8.989 documentos...</p>\n";

try {
    // Conectar MongoDB
    $manager = new MongoDB\Driver\Manager(MONGO_CONNECTION_STRING);
    echo "✅ Conectado ao MongoDB<br>\n";

    // Contar total de documentos
    $pipeline = [['$count' => 'total']];
    $command = new MongoDB\Driver\Command([
        'aggregate' => 'coletores',
        'pipeline' => $pipeline,
        'cursor' => new stdClass,
    ]);
    $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
    $result = $cursor->toArray();
    $total = isset($result[0]->total) ? $result[0]->total : 0;

    echo "📊 Total de documentos: " . number_format($total, 0, ',', '.') . "<br>\n";

    // Processar em lotes de 1000
    $loteSize = 1000;
    $loteAtual = 0;
    $totalProcessados = 0;

    echo "<h3>Processando em lotes de $loteSize:</h3>\n";

    while ($totalProcessados < $total) {
        $skip = $loteAtual * $loteSize;
        echo "📦 Lote " . ($loteAtual + 1) . " (documentos " . ($skip + 1) . " a " . min($skip + $loteSize, $total) . ")...<br>\n";

        // Buscar lote
        $query = new MongoDB\Driver\Query([], ['skip' => $skip, 'limit' => $loteSize]);
        $cursor = $manager->executeQuery(MONGO_DATABASE . '.coletores', $query);
        $documents = $cursor->toArray();

        if (empty($documents)) {
            echo "⚠️ Nenhum documento no lote, parando...<br>\n";
            break;
        }

        // Preparar para MeiliSearch
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
                'variacoes' => $variacoes,
                'kingdom' => $doc->kingdom ?? [],
                'confianca_canonicalizacao' => $doc->confianca_canonicalizacao ?? 0,
                'confianca_tipo_coletor' => $doc->confianca_tipo_coletor ?? 0
            ];
        }

        // Indexar lote
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
        curl_setopt($ch, CURLOPT_TIMEOUT, 30);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode === 202) {
            echo "✅ Lote indexado com sucesso<br>\n";
        } else {
            echo "❌ Erro no lote: $httpCode<br>\n";
            break;
        }

        $totalProcessados += count($documents);
        $loteAtual++;

        // Pausa entre lotes para não sobrecarregar
        sleep(1);

        // Mostrar progresso a cada 5 lotes
        if ($loteAtual % 5 === 0) {
            $porcentagem = round(($totalProcessados / $total) * 100, 1);
            echo "<strong>📈 Progresso: $totalProcessados de $total documentos ($porcentagem%)</strong><br>\n";
            echo "<script>window.scrollTo(0, document.body.scrollHeight);</script>\n";
            flush();
        }
    }

    echo "<br><h3>✅ Indexação Concluída!</h3>\n";
    echo "📊 Total processado: " . number_format($totalProcessados, 0, ',', '.') . " documentos<br>\n";
    echo "⏳ Aguarde alguns minutos para o MeiliSearch processar todos os dados<br>\n";

    // Teste final
    echo "<h3>Teste da busca:</h3>\n";
    sleep(5); // Aguardar um pouco

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
        echo "📊 Documentos indexados: " . count($result['hits'] ?? []) . "<br>\n";
    } else {
        echo "⚠️ Busca ainda processando...<br>\n";
    }

} catch (Exception $e) {
    echo "❌ Erro: " . $e->getMessage() . "<br>\n";
}

echo "<br><hr><br>";
echo "<a href='index.php'>🏠 Ir para página principal</a>";
?>