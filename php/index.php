<?php
require_once 'config.php';

// Verificar se a extensão MongoDB está disponível
if (!extension_loaded('mongodb')) {
    die('Extensão MongoDB não está instalada. Execute: composer require mongodb/mongodb');
}

// Função para conectar ao MongoDB
function connectMongoDB() {
    try {
        // Usar string de conexão completa se disponível, senão construir
        if (defined('MONGO_CONNECTION_STRING')) {
            $connectionString = MONGO_CONNECTION_STRING;
        } else {
            // Verificar se as constantes estão definidas
            if (!defined('MONGO_HOST') || !defined('MONGO_PORT')) {
                throw new Exception('Configurações do MongoDB não encontradas');
            }

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
            } else {
                $connectionString = "mongodb://" . MONGO_HOST . ":" . MONGO_PORT;
            }
        }

        $manager = new MongoDB\Driver\Manager($connectionString);

        // Para usuários read-only, vamos testar a conexão fazendo uma query simples
        // ao invés de usar ping ou listCollections que podem exigir permissões especiais
        try {
            $query = new MongoDB\Driver\Query([], ['limit' => 1]);
            $cursor = $manager->executeQuery(MONGO_DATABASE . '.' . MONGO_COLLECTION, $query);
            // Se chegou aqui, a conexão está funcionando
        } catch (Exception $e) {
            throw new Exception('Falha ao testar conexão: ' . $e->getMessage());
        }

        return $manager;
    } catch (Exception $e) {
        error_log("Erro ao conectar ao MongoDB: " . $e->getMessage());
        return null;
    }
}

// Função para obter estatísticas da base de dados
function getDatabaseStats() {
    $manager = connectMongoDB();
    if (!$manager) {
        // Verificar se as configurações estão definidas para debug
        $debug_info = "Debug: ";
        $debug_info .= defined('MONGO_HOST') ? "HOST=".MONGO_HOST." " : "HOST=INDEFINIDO ";
        $debug_info .= defined('MONGO_USERNAME') ? "USER=".MONGO_USERNAME." " : "USER=INDEFINIDO ";
        $debug_info .= defined('MONGO_DATABASE') ? "DB=".MONGO_DATABASE." " : "DB=INDEFINIDO ";
        $debug_info .= defined('MONGO_CONNECTION_STRING') ? "CONN_STRING=DEFINIDA " : "CONN_STRING=INDEFINIDA ";

        return ['error' => 'Não foi possível conectar ao MongoDB. ' . $debug_info];
    }

    try {
        // Verificar se as constantes necessárias estão definidas
        if (!defined('MONGO_DATABASE') || !defined('MONGO_COLLECTION')) {
            return ['error' => 'Configurações da base de dados não encontradas'];
        }

        // Total de coletores usando aggregate (mais compatível com read-only)
        $pipeline = [
            ['$count' => 'total']
        ];
        $command = new MongoDB\Driver\Command([
            'aggregate' => MONGO_COLLECTION,
            'pipeline' => $pipeline,
            'cursor' => new stdClass,
        ]);

        $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
        $result = $cursor->toArray();
        $totalColetores = isset($result[0]->total) ? $result[0]->total : 0;

        // Estatísticas por tipo
        $pipeline = [
            ['$group' => [
                '_id' => '$tipo_coletor',
                'count' => ['$sum' => 1]
            ]],
            ['$sort' => ['count' => -1]]
        ];

        $command = new MongoDB\Driver\Command([
            'aggregate' => MONGO_COLLECTION,
            'pipeline' => $pipeline,
            'cursor' => new stdClass,
        ]);

        $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
        $estatisticasTipo = $cursor->toArray();

        // Top 10 coletores com mais registros
        $pipeline = [
            ['$match' => ['total_registros' => ['$gt' => 0]]],
            ['$sort' => ['total_registros' => -1]],
            ['$limit' => 10],
            ['$project' => [
                'coletor_canonico' => 1,
                'total_registros' => 1
            ]]
        ];

        $command = new MongoDB\Driver\Command([
            'aggregate' => MONGO_COLLECTION,
            'pipeline' => $pipeline,
            'cursor' => new stdClass,
        ]);

        $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
        $topColetores = $cursor->toArray();

        // Estatísticas adicionais criativas
        $metadados = getMetadadosProcessamento($manager);

        return [
            'total_coletores' => $totalColetores,
            'estatisticas_tipo' => $estatisticasTipo,
            'top_coletores' => $topColetores,
            'metadados' => $metadados,
            'success' => true
        ];
    } catch (Exception $e) {
        $errorMsg = "Erro ao obter estatísticas: " . $e->getMessage();
        error_log($errorMsg);
        return ['error' => $errorMsg];
    }
}

// Função para obter metadados de processamento (criativos)
function getMetadadosProcessamento($manager) {
    try {
        // Estatísticas de confiança
        $pipeline = [
            ['$group' => [
                '_id' => null,
                'confianca_alta' => ['$sum' => ['$cond' => [['$gte' => ['$confianca_canonicalizacao', 0.9]], 1, 0]]],
                'confianca_media' => ['$sum' => ['$cond' => [['$and' => [['$gte' => ['$confianca_canonicalizacao', 0.7]], ['$lt' => ['$confianca_canonicalizacao', 0.9]]]], 1, 0]]],
                'confianca_baixa' => ['$sum' => ['$cond' => [['$lt' => ['$confianca_canonicalizacao', 0.7]], 1, 0]]],
                'total_variacoes' => ['$sum' => ['$size' => '$variacoes']],
                'coletor_mais_variacoes' => ['$max' => ['$size' => '$variacoes']],
                'total_registros_geral' => ['$sum' => '$total_registros']
            ]]
        ];

        $command = new MongoDB\Driver\Command([
            'aggregate' => MONGO_COLLECTION,
            'pipeline' => $pipeline,
            'cursor' => new stdClass,
        ]);

        $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
        $result = $cursor->toArray();
        $stats = isset($result[0]) ? $result[0] : null;

        // Coletor com mais variações
        $query = new MongoDB\Driver\Query([], [
            'sort' => ['$expr' => ['$size' => '$variacoes']],
            'limit' => 1
        ]);

        // Usar agregação para encontrar o coletor com mais variações
        $pipeline2 = [
            ['$addFields' => ['num_variacoes' => ['$size' => '$variacoes']]],
            ['$sort' => ['num_variacoes' => -1]],
            ['$limit' => 1]
        ];

        $command2 = new MongoDB\Driver\Command([
            'aggregate' => MONGO_COLLECTION,
            'pipeline' => $pipeline2,
            'cursor' => new stdClass,
        ]);

        $cursor2 = $manager->executeCommand(MONGO_DATABASE, $command2);
        $maisVariacoes = $cursor2->toArray();

        return [
            'estatisticas_confianca' => $stats,
            'coletor_mais_variacoes' => isset($maisVariacoes[0]) ? $maisVariacoes[0] : null,
            'algoritmo_versao' => '1.0',
            'data_processamento' => date('Y-m-d'),
            'indices_soundex' => true,
            'indices_metaphone' => true
        ];

    } catch (Exception $e) {
        return null;
    }
}

// Função para buscar coletor por ID
function getColetorById($id) {
    $manager = connectMongoDB();
    if (!$manager) return null;

    try {
        $filter = ['_id' => new MongoDB\BSON\ObjectId($id)];
        $query = new MongoDB\Driver\Query($filter);
        $cursor = $manager->executeQuery(MONGO_DATABASE . '.' . MONGO_COLLECTION, $query);
        $result = $cursor->toArray();
        return count($result) > 0 ? $result[0] : null;
    } catch (Exception $e) {
        error_log("Erro ao buscar coletor: " . $e->getMessage());
        return null;
    }
}

// Função para buscar exemplos por tipo de coletor
function getExemplosPorTipo($tipo) {
    $manager = connectMongoDB();
    if (!$manager) return null;

    try {
        // Filtro baseado no tipo
        $filter = $tipo ? ['tipo_coletor' => $tipo] : ['tipo_coletor' => ['$exists' => false]];

        // Buscar 10 exemplos, ordenados por total_registros
        $query = new MongoDB\Driver\Query($filter, [
            'limit' => 10,
            'sort' => ['total_registros' => -1]
        ]);

        $cursor = $manager->executeQuery(MONGO_DATABASE . '.' . MONGO_COLLECTION, $query);
        $exemplos = $cursor->toArray();

        // Estatísticas do tipo
        $pipeline = [
            ['$match' => $filter],
            ['$group' => [
                '_id' => null,
                'total_coletores' => ['$sum' => 1],
                'total_registros' => ['$sum' => '$total_registros'],
                'media_registros' => ['$avg' => '$total_registros'],
                'max_registros' => ['$max' => '$total_registros'],
                'confianca_media' => ['$avg' => '$confianca_canonicalizacao']
            ]]
        ];

        $command = new MongoDB\Driver\Command([
            'aggregate' => MONGO_COLLECTION,
            'pipeline' => $pipeline,
            'cursor' => new stdClass,
        ]);

        $cursor = $manager->executeCommand(MONGO_DATABASE, $command);
        $estatisticas = $cursor->toArray();
        $stats = isset($estatisticas[0]) ? $estatisticas[0] : null;

        return [
            'tipo' => $tipo ?: 'Não especificado',
            'exemplos' => $exemplos,
            'estatisticas' => $stats
        ];

    } catch (Exception $e) {
        error_log("Erro ao buscar exemplos por tipo: " . $e->getMessage());
        return null;
    }
}

// Processar requisições AJAX
if (isset($_GET['action'])) {
    header('Content-Type: application/json');

    if ($_GET['action'] === 'search' && isset($_GET['q'])) {
        // Busca via MeiliSearch
        $query = trim($_GET['q']);
        if (strlen($query) < 2) {
            echo json_encode(['hits' => []]);
            exit;
        }

        $url = MEILISEARCH_HOST . '/indexes/' . MEILISEARCH_INDEX . '/search';
        $data = json_encode([
            'q' => $query,
            'limit' => 20,
            'attributesToHighlight' => ['coletor_canonico', 'variacoes'],
            'highlightPreTag' => '<mark>',
            'highlightPostTag' => '</mark>'
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
        curl_close($ch);

        echo $response;
        exit;
    }

    if ($_GET['action'] === 'get_coletor' && isset($_GET['id'])) {
        $coletor = getColetorById($_GET['id']);
        echo json_encode($coletor);
        exit;
    }

    if ($_GET['action'] === 'get_tipo' && isset($_GET['tipo'])) {
        $tipo = $_GET['tipo'] === 'nao_especificado' ? null : $_GET['tipo'];
        $exemplos = getExemplosPorTipo($tipo);
        echo json_encode($exemplos);
        exit;
    }
}

$stats = getDatabaseStats();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo APP_TITLE; ?> - Nova Versão</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: linear-gradient(135deg, #2c5530, #3d7c47);
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
            border-radius: 8px;
        }

        .header h1 {
            text-align: center;
            margin-bottom: 0.5rem;
        }

        .header p {
            text-align: center;
            opacity: 0.9;
        }

        .search-section {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }

        .search-box {
            position: relative;
            margin-bottom: 1rem;
        }

        #searchInput {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 6px;
            outline: none;
            transition: border-color 0.3s;
        }

        #searchInput:focus {
            border-color: #3d7c47;
        }

        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 6px 6px;
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
        }

        .search-result-item {
            padding: 12px 16px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
        }

        .search-result-item:hover {
            background-color: #f8f9fa;
        }

        .search-result-item:last-child {
            border-bottom: none;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .stats-card {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .stats-card h3 {
            color: #2c5530;
            margin-bottom: 1rem;
            border-bottom: 2px solid #3d7c47;
            padding-bottom: 0.5rem;
        }

        .stat-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #eee;
        }

        .stat-item:last-child {
            border-bottom: none;
        }

        .coletor-details {
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: none;
        }

        .detail-section {
            margin-bottom: 2rem;
        }

        .detail-section h4 {
            color: #2c5530;
            margin-bottom: 1rem;
            border-left: 4px solid #3d7c47;
            padding-left: 1rem;
        }

        .variantes-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .variante-tag {
            background: #e8f5e8;
            color: #2c5530;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.9rem;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }

        mark {
            background: #fff3cd;
            padding: 0.1rem 0.2rem;
            border-radius: 3px;
        }

        .back-button {
            background: #6c757d;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            margin-bottom: 1rem;
        }

        .back-button:hover {
            background: #5a6268;
        }

        .error-card {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><?php echo APP_TITLE; ?> - Nova Versão</h1>
            <p>Sistema de consulta e estatísticas da base de dados de coletores</p>
        </div>

        <div class="search-section">
            <h2>Buscar Coletor</h2>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Digite o nome do coletor..." autocomplete="off">
                <div class="search-results" id="searchResults"></div>
            </div>
        </div>

        <div id="statsSection">
            <?php if ($stats && isset($stats['success'])): ?>
            <div class="stats-grid">
                <div class="stats-card">
                    <h3>Resumo Geral</h3>
                    <div class="stat-item">
                        <span>Total de Coletores:</span>
                        <strong><?php echo number_format($stats['total_coletores'], 0, ',', '.'); ?></strong>
                    </div>
                    <?php if (isset($stats['metadados']) && $stats['metadados']): ?>
                        <?php $meta = $stats['metadados']; ?>
                        <?php if (isset($meta['estatisticas_confianca'])): ?>
                            <?php $conf = $meta['estatisticas_confianca']; ?>
                            <div class="stat-item">
                                <span>📊 Total de Registros:</span>
                                <strong><?php echo number_format($conf->total_registros_geral ?? 0, 0, ',', '.'); ?></strong>
                            </div>
                            <div class="stat-item">
                                <span>🎯 Confiança Alta (≥90%):</span>
                                <strong><?php echo number_format($conf->confianca_alta ?? 0, 0, ',', '.'); ?></strong>
                            </div>
                            <div class="stat-item">
                                <span>🔍 Total de Variações:</span>
                                <strong><?php echo number_format($conf->total_variacoes ?? 0, 0, ',', '.'); ?></strong>
                            </div>
                            <div class="stat-item">
                                <span>🧠 Algoritmo:</span>
                                <strong>v<?php echo $meta['algoritmo_versao']; ?> + Soundex + Metaphone</strong>
                            </div>
                        <?php endif; ?>
                    <?php endif; ?>
                </div>

                <div class="stats-card">
                    <h3>Por Tipo de Coletor</h3>
                    <?php if (!empty($stats['estatisticas_tipo'])): ?>
                        <?php foreach ($stats['estatisticas_tipo'] as $stat): ?>
                        <div class="stat-item">
                            <span style="cursor: pointer; color: #3d7c47; text-decoration: underline;" onclick="mostrarTipoColetor('<?php echo htmlspecialchars($stat->_id ?: 'nao_especificado'); ?>')"><?php echo $stat->_id ?: 'Não especificado'; ?>:</span>
                            <strong><?php echo number_format($stat->count, 0, ',', '.'); ?></strong>
                        </div>
                        <?php endforeach; ?>
                    <?php else: ?>
                        <p>Nenhum dado encontrado.</p>
                    <?php endif; ?>
                </div>

                <div class="stats-card">
                    <h3>Top 10 Coletores</h3>
                    <?php if (!empty($stats['top_coletores'])): ?>
                        <?php foreach ($stats['top_coletores'] as $coletor): ?>
                        <div class="stat-item">
                            <span style="cursor: pointer; color: #3d7c47; text-decoration: underline;" onclick="selecionarColetor('<?php echo (string)$coletor->_id; ?>')"><?php echo htmlspecialchars($coletor->coletor_canonico); ?>:</span>
                            <strong><?php echo number_format($coletor->total_registros, 0, ',', '.'); ?> registros</strong>
                        </div>
                        <?php endforeach; ?>
                    <?php else: ?>
                        <p>Nenhum dado encontrado.</p>
                    <?php endif; ?>
                </div>
            </div>
            <?php else: ?>
            <div class="stats-card">
                <h3>❌ Erro na Base de Dados</h3>
                <?php if ($stats && isset($stats['error'])): ?>
                    <div class="error-card">
                        <strong>Detalhes:</strong> <?php echo htmlspecialchars($stats['error']); ?>
                    </div>
                <?php endif; ?>

                <h4>Verificações necessárias:</h4>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>MongoDB está rodando?</li>
                    <li>Extensão MongoDB PHP está instalada?</li>
                    <li>Configurações em config.php estão corretas?</li>
                    <li>Base de dados "<?php echo MONGO_DATABASE; ?>" existe?</li>
                    <li>Coleção "<?php echo MONGO_COLLECTION; ?>" existe?</li>
                </ul>

                <p><a href="test_conexao.php">📋 Executar teste de diagnóstico completo</a></p>
            </div>
            <?php endif; ?>
        </div>

        <div class="coletor-details" id="coletorDetails">
            <button class="back-button" onclick="voltarEstatisticas()">← Voltar às Estatísticas</button>
            <div id="coletorContent"></div>
        </div>
    </div>

    <script>
        let searchTimeout;
        const searchInput = document.getElementById('searchInput');
        const searchResults = document.getElementById('searchResults');
        const statsSection = document.getElementById('statsSection');
        const coletorDetails = document.getElementById('coletorDetails');
        const coletorContent = document.getElementById('coletorContent');

        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length < 2) {
                searchResults.style.display = 'none';
                return;
            }

            searchTimeout = setTimeout(() => {
                buscarColetores(query);
            }, 300);
        });

        searchInput.addEventListener('focus', function() {
            if (searchResults.children.length > 0) {
                searchResults.style.display = 'block';
            }
        });

        document.addEventListener('click', function(e) {
            if (!e.target.closest('.search-box')) {
                searchResults.style.display = 'none';
            }
        });

        function buscarColetores(query) {
            fetch(`?action=search&q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    mostrarResultadosBusca(data.hits || []);
                })
                .catch(error => {
                    console.error('Erro na busca:', error);
                    searchResults.innerHTML = '<div class="search-result-item">Erro ao buscar coletores</div>';
                    searchResults.style.display = 'block';
                });
        }

        function mostrarResultadosBusca(hits) {
            if (hits.length === 0) {
                searchResults.innerHTML = '<div class="search-result-item">Nenhum resultado encontrado</div>';
            } else {
                searchResults.innerHTML = hits.map(hit => `
                    <div class="search-result-item" onclick="selecionarColetor('${hit.id}')">
                        <div><strong>${hit._formatted?.coletor_canonico || hit.coletor_canonico}</strong></div>
                        <div style="font-size: 0.9em; color: #666;">
                            ${hit.tipo_coletor || 'Tipo não especificado'} •
                            ${hit.total_registros || 0} registros
                        </div>
                    </div>
                `).join('');
            }
            searchResults.style.display = 'block';
        }

        function selecionarColetor(id) {
            searchResults.style.display = 'none';
            coletorContent.innerHTML = '<div class="loading">Carregando dados do coletor...</div>';
            statsSection.style.display = 'none';
            coletorDetails.style.display = 'block';

            fetch(`?action=get_coletor&id=${id}`)
                .then(response => response.json())
                .then(coletor => {
                    if (coletor) {
                        mostrarDetalhesColetor(coletor);
                    } else {
                        coletorContent.innerHTML = '<p>Coletor não encontrado.</p>';
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar coletor:', error);
                    coletorContent.innerHTML = '<p>Erro ao carregar dados do coletor.</p>';
                });
        }

        function mostrarDetalhesColetor(coletor) {
            const variacoes = coletor.variacoes || [];
            const totalRegistros = coletor.total_registros || 0;

            let html = `
                <h2>${coletor.coletor_canonico}</h2>

                <div class="detail-section">
                    <h4>Informações Básicas</h4>
                    <div class="stat-item">
                        <span>Tipo de Coletor:</span>
                        <strong>${coletor.tipo_coletor || 'Não especificado'}</strong>
                    </div>
                    <div class="stat-item">
                        <span>Total de Registros:</span>
                        <strong>${totalRegistros}</strong>
                    </div>
                </div>
            `;

            if (variacoes.length > 0) {
                html += `
                    <div class="detail-section">
                        <h4>Variações do Nome (${variacoes.length})</h4>
                        <div class="variantes-list">
                            ${variacoes.map(v => `<span class="variante-tag">${v.forma_original || v}</span>`).join('')}
                        </div>
                    </div>
                `;
            }

            // Mostrar informações adicionais se disponíveis
            if (coletor.kingdom && coletor.kingdom.length > 0) {
                html += `
                    <div class="detail-section">
                        <h4>Reinos Associados</h4>
                        <div class="variantes-list">
                            ${coletor.kingdom.map(k => `<span class="variante-tag">${k}</span>`).join('')}
                        </div>
                    </div>
                `;
            }

            if (coletor.confianca_canonicalizacao) {
                html += `
                    <div class="detail-section">
                        <h4>Metadados</h4>
                        <div class="stat-item">
                            <span>Confiança da Canonicalização:</span>
                            <strong>${Math.round(coletor.confianca_canonicalizacao * 100)}%</strong>
                        </div>
                        <div class="stat-item">
                            <span>Confiança do Tipo:</span>
                            <strong>${Math.round((coletor.confianca_tipo_coletor || 0) * 100)}%</strong>
                        </div>
                    </div>
                `;
            }

            coletorContent.innerHTML = html;
        }

        function mostrarTipoColetor(tipo) {
            coletorContent.innerHTML = '<div class="loading">Carregando exemplos do tipo...</div>';
            statsSection.style.display = 'none';
            coletorDetails.style.display = 'block';

            fetch(`?action=get_tipo&tipo=${encodeURIComponent(tipo)}`)
                .then(response => response.json())
                .then(data => {
                    if (data) {
                        mostrarDetalhesTipo(data);
                    } else {
                        coletorContent.innerHTML = '<p>Erro ao carregar exemplos.</p>';
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar tipo:', error);
                    coletorContent.innerHTML = '<p>Erro ao carregar dados do tipo.</p>';
                });
        }

        function mostrarDetalhesTipo(data) {
            const stats = data.estatisticas;
            const exemplos = data.exemplos || [];

            let html = `
                <h2>Tipo: ${data.tipo}</h2>

                <div class="detail-section">
                    <h4>Estatísticas do Tipo</h4>
                    ${stats ? `
                        <div class="stat-item">
                            <span>Total de Coletores:</span>
                            <strong>${stats.total_coletores ? stats.total_coletores.toLocaleString() : 0}</strong>
                        </div>
                        <div class="stat-item">
                            <span>Total de Registros:</span>
                            <strong>${stats.total_registros ? stats.total_registros.toLocaleString() : 0}</strong>
                        </div>
                        <div class="stat-item">
                            <span>Média de Registros por Coletor:</span>
                            <strong>${stats.media_registros ? Math.round(stats.media_registros).toLocaleString() : 0}</strong>
                        </div>
                        <div class="stat-item">
                            <span>Máximo de Registros:</span>
                            <strong>${stats.max_registros ? stats.max_registros.toLocaleString() : 0}</strong>
                        </div>
                        <div class="stat-item">
                            <span>Confiança Média:</span>
                            <strong>${stats.confianca_media ? Math.round(stats.confianca_media * 100) + '%' : 'N/A'}</strong>
                        </div>
                    ` : '<p>Estatísticas não disponíveis</p>'}
                </div>

                <div class="detail-section">
                    <h4>Top 10 Exemplos</h4>
                    ${exemplos.length > 0 ? exemplos.map(ex => `
                        <div class="stat-item">
                            <span style="cursor: pointer; color: #3d7c47; text-decoration: underline;" onclick="selecionarColetor('${ex._id}')">${ex.coletor_canonico}</span>
                            <strong>${ex.total_registros ? ex.total_registros.toLocaleString() : 0} registros</strong>
                        </div>
                    `).join('') : '<p>Nenhum exemplo encontrado</p>'}
                </div>
            `;

            coletorContent.innerHTML = html;
        }

        function voltarEstatisticas() {
            coletorDetails.style.display = 'none';
            statsSection.style.display = 'block';
            searchInput.value = '';
            searchResults.style.display = 'none';
        }
    </script>
</body>
</html>