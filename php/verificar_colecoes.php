<?php
require_once 'config.php';

echo "<h2>Verificar Coleções - Biodiversidade Online</h2>\n";

try {
    $manager = new MongoDB\Driver\Manager(MONGO_CONNECTION_STRING);

    // Listar todas as coleções
    echo "<h3>Coleções na base de dados '" . MONGO_DATABASE . "':</h3>\n";

    $command = new MongoDB\Driver\Command(['listCollections' => 1]);
    $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
    $collections = $cursor->toArray();

    echo "<ul>\n";
    foreach ($collections as $collection) {
        echo "<li><strong>" . $collection->name . "</strong>";

        // Contar documentos em cada coleção
        try {
            $pipeline = [['$count' => 'total']];
            $command = new MongoDB\Driver\Command([
                'aggregate' => $collection->name,
                'pipeline' => $pipeline,
                'cursor' => new stdClass,
            ]);
            $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
            $result = $cursor->toArray();
            $count = isset($result[0]->total) ? $result[0]->total : 0;
            echo " - " . number_format($count, 0, ',', '.') . " documentos";
        } catch (Exception $e) {
            echo " - erro ao contar";
        }
        echo "</li>\n";
    }
    echo "</ul>\n";

    // Verificar especificamente a coleção coletores
    echo "<h3>Verificação da coleção 'coletores':</h3>\n";
    $coletoresExists = false;
    foreach ($collections as $collection) {
        if ($collection->name === 'coletores') {
            $coletoresExists = true;
            break;
        }
    }

    if ($coletoresExists) {
        echo "✅ Coleção 'coletores' existe<br>\n";

        // Buscar um documento de exemplo
        $query = new MongoDB\Driver\Query([], ['limit' => 1]);
        $cursor = $manager->executeQuery(MONGO_DATABASE . '.coletores', $query);
        $documents = $cursor->toArray();

        if (!empty($documents)) {
            echo "<h4>Exemplo de documento na coleção 'coletores':</h4>\n";
            echo "<pre>" . json_encode($documents[0], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "</pre>\n";
        }
    } else {
        echo "❌ Coleção 'coletores' NÃO existe<br>\n";
        echo "<br>Sugestões:<br>\n";
        echo "- Use 'taxaOccurence' se for para dados de espécies<br>\n";
        echo "- Verifique se existe outra coleção com nome similar<br>\n";
    }

    // Verificar coleção taxaOccurence (da aplicação funcionando)
    echo "<h3>Verificação da coleção 'taxaOccurence':</h3>\n";
    $taxaExists = false;
    foreach ($collections as $collection) {
        if ($collection->name === 'taxaOccurence') {
            $taxaExists = true;
            break;
        }
    }

    if ($taxaExists) {
        echo "✅ Coleção 'taxaOccurence' existe<br>\n";

        // Buscar um documento de exemplo
        $query = new MongoDB\Driver\Query([], ['limit' => 1]);
        $cursor = $manager->executeQuery(MONGO_DATABASE . '.taxaOccurence', $query);
        $documents = $cursor->toArray();

        if (!empty($documents)) {
            echo "<h4>Exemplo de documento na coleção 'taxaOccurence':</h4>\n";
            echo "<pre>" . json_encode($documents[0], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . "</pre>\n";
        }
    } else {
        echo "❌ Coleção 'taxaOccurence' NÃO existe<br>\n";
    }

} catch (Exception $e) {
    echo "❌ Erro: " . $e->getMessage();
}

echo "<br><hr><br>";
echo "<a href='index.php'>← Voltar para a página principal</a>";
?>