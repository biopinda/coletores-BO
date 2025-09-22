<?php
// Arquivo de exemplo de configurações
// Copie este arquivo para config.php e preencha com suas credenciais

// Configurações do MongoDB
define('MONGO_HOST', 'localhost');
define('MONGO_PORT', 27017);
define('MONGO_DATABASE', 'dwc2json');
define('MONGO_COLLECTION', 'coletores');

// Credenciais do MongoDB (se necessário)
define('MONGO_USERNAME', 'seu-usuario');
define('MONGO_PASSWORD', 'sua-senha');

// Configurações do MeiliSearch
define('MEILISEARCH_HOST', 'http://seu-host:7700');
define('MEILISEARCH_KEY', 'sua-chave-secreta');
define('MEILISEARCH_INDEX', 'coletores');

// Configurações da aplicação
define('APP_TITLE', 'Biodiversidade Online - Coletores');
define('APP_VERSION', '1.0.0');
?>