// ---------------------------------------------------------------------------
// Georgia DCH Certificate of Need (CON) research database — infrastructure.
//
// Resource-group scope deployment. Orchestrates modules under ./modules.
// See infra/README.md for prerequisites, deploy commands, and post-deploy
// steps (SQL users for managed identities, Key Vault secrets, Easy Auth).
// ---------------------------------------------------------------------------
targetScope = 'resourceGroup'

// ----------------------------- parameters ----------------------------------

@description('Short name prefix for all resources (lowercase letters, digits, hyphens), e.g. "gacon". Combined with environment: "<namePrefix>-<environment>-<suffix>".')
@minLength(3)
@maxLength(12)
param namePrefix string = 'gacon'

@description('Environment name, used in resource names and tags.')
@allowed(['dev', 'test', 'prod'])
param environment string = 'dev'

@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Tags applied to every resource.')
param tags object = {
  project: 'ga-con-database'
  environment: environment
}

@description('Object ID (Entra ID) of the user or group to set as the Azure SQL server administrator. The server is AAD-only; this principal runs migrations and creates database users for the managed identities.')
param sqlAdminObjectId string

@description('Login name shown for the Entra SQL administrator — the group display name or user UPN matching sqlAdminObjectId.')
param sqlAdminLogin string

@description('Principal type of the Entra SQL administrator.')
@allowed(['User', 'Group', 'Application'])
param sqlAdminPrincipalType string = 'Group'

@description('Tenant ID of the Entra SQL administrator. Defaults to the deployment tenant.')
param sqlAdminTenantId string = tenant().tenantId

@description('Name of the application database.')
param sqlDatabaseName string = 'condb'

@description('Allow public network access to the SQL server (with the AllowAzureServices firewall rule). Set false once private endpoints are in place — see README "Hardening".')
param enablePublicNetworkAccess bool = true

@description('Deploy Azure AI Search (basic tier) for /search/semantic and /ask.')
param deploySearch bool = true

@description('Semantic ranker plan for Azure AI Search. "free" caps at 1,000 requests/month; "standard" is billed per request.')
@allowed(['disabled', 'free', 'standard'])
param searchSemanticSearch string = 'free'

@description('Deploy an Azure OpenAI account with gpt-4o-mini and text-embedding-3-small deployments. Default false: regional availability and quota vary — see README.')
param deployOpenAI bool = false

@description('Capacity (thousands of tokens-per-minute) for the gpt-4o-mini Standard deployment.')
param openAiChatCapacity int = 8

@description('Capacity (thousands of tokens-per-minute) for the text-embedding-3-small Standard deployment.')
param openAiEmbeddingCapacity int = 50

@description('Model version for the gpt-4o-mini deployment.')
param openAiChatModelVersion string = '2024-07-18'

@description('Model version for the text-embedding-3-small deployment.')
param openAiEmbeddingModelVersion string = '1'

@description('NCRONTAB expression for the daily catch-up sweep timer in the function app (SWEEP_CRON).')
param sweepCron string = '0 0 6 * * *'

@description('Whether SQL full-text search is enabled for the API (FULLTEXT_ENABLED app setting). Requires the full-text migration to have been applied.')
param fulltextEnabled bool = true

@description('Log Analytics data retention in days.')
@minValue(30)
@maxValue(730)
param logRetentionDays int = 30

@description('Append uniqueString(resourceGroup().id) to the storage account name for global uniqueness.')
param useUniqueStorageSuffix bool = true

// --- Research layer (v2): console + document-text extraction ------------------

@description('Deploy an Azure Static Web App (Free plan) to host the React research console in web/.')
param deployStaticWebApp bool = true

@description('Region for the Static Web App. Static Web Apps are offered in a limited set of regions (e.g. westus2, centralus, eastus2, westeurope, eastasia); override if the resource group region is unsupported. Defaults to the deployment location.')
param staticWebAppLocation string = location

@description('Deploy an Azure AI Document Intelligence account for the document-text extraction step.')
param deployDocIntel bool = true

@description('Document Intelligence pricing tier. F0 is free (500 pages/month); S0 is standard pay-as-you-go for backfills that exceed the free monthly limit. See README cost table.')
@allowed(['F0', 'S0'])
param docIntelSku string = 'F0'

@description('Enable the Azure SQL Database free offer (GP serverless: 100k vCore-seconds + 32 GB data + 32 GB backup free per month, per database). See README "Enable the SQL free offer".')
param sqlUseFreeOffer bool = true

// ----------------------------- variables ------------------------------------

var baseName = toLower('${namePrefix}-${environment}')

// Storage account names: 3-24 chars, lowercase alphanumeric only.
var storagePrefix = toLower(replace(replace(namePrefix, '-', ''), '_', ''))
var storageSuffix = useUniqueStorageSuffix ? uniqueString(resourceGroup().id) : ''
var storageAccountName = take('${storagePrefix}${toLower(environment)}st${storageSuffix}', 24)

var snapshotContainer = 'index-snapshots'
var reportContainer = 'weekly-reports'
// document-text: raw text extracted by Document Intelligence, consumed by
// ingest/load_document_text.py to populate con.document_text.
var documentTextContainer = 'document-text'
var blobContainers = [snapshotContainer, reportContainer, 'tag-exports', documentTextContainer]

var searchIndexName = 'con-records'
var chatDeploymentName = 'gpt-4o-mini'
var embeddingDeploymentName = 'text-embedding-3-small'

// ----------------------------- modules --------------------------------------

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    workspaceName: '${baseName}-log'
    appInsightsName: '${baseName}-appi'
    location: location
    tags: tags
    retentionInDays: logRetentionDays
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    storageAccountName: storageAccountName
    location: location
    tags: tags
    containerNames: blobContainers
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    keyVaultName: '${baseName}-kv'
    location: location
    tags: tags
  }
}

module sql 'modules/sql.bicep' = {
  name: 'sql'
  params: {
    serverName: '${baseName}-sql'
    databaseName: sqlDatabaseName
    location: location
    tags: tags
    adminLogin: sqlAdminLogin
    adminObjectId: sqlAdminObjectId
    adminTenantId: sqlAdminTenantId
    adminPrincipalType: sqlAdminPrincipalType
    enablePublicNetworkAccess: enablePublicNetworkAccess
    sqlUseFreeOffer: sqlUseFreeOffer
  }
}

module search 'modules/search.bicep' = if (deploySearch) {
  name: 'search'
  params: {
    searchServiceName: '${baseName}-search'
    location: location
    tags: tags
    semanticSearch: searchSemanticSearch
  }
}

module openAi 'modules/openai.bicep' = if (deployOpenAI) {
  name: 'openai'
  params: {
    accountName: '${baseName}-aoai'
    location: location
    tags: tags
    chatDeploymentName: chatDeploymentName
    chatModelVersion: openAiChatModelVersion
    chatCapacity: openAiChatCapacity
    embeddingDeploymentName: embeddingDeploymentName
    embeddingModelVersion: openAiEmbeddingModelVersion
    embeddingCapacity: openAiEmbeddingCapacity
  }
}

module staticWebApp 'modules/staticwebapp.bicep' = if (deployStaticWebApp) {
  name: 'staticwebapp'
  params: {
    staticWebAppName: '${baseName}-web'
    location: staticWebAppLocation
    tags: tags
    sku: 'Free'
  }
}

module docIntel 'modules/docintelligence.bicep' = if (deployDocIntel) {
  name: 'docintel'
  params: {
    accountName: '${baseName}-di'
    location: location
    tags: tags
    docIntelSku: docIntelSku
  }
}

var searchEndpoint = deploySearch ? search!.outputs.endpoint : ''
var azureOpenAiEndpoint = deployOpenAI ? openAi!.outputs.endpoint : ''
var docIntelEndpoint = deployDocIntel ? docIntel!.outputs.endpoint : ''
var consoleOrigin = deployStaticWebApp ? 'https://${staticWebApp!.outputs.defaultHostName}' : ''

module functions 'modules/functions.bicep' = {
  name: 'functions'
  params: {
    planName: '${baseName}-func-plan'
    functionAppName: '${baseName}-func'
    location: location
    tags: tags
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    sqlServerFqdn: sql.outputs.serverFqdn
    sqlDatabaseName: sql.outputs.databaseName
    snapshotContainer: snapshotContainer
    reportContainer: reportContainer
    sweepCron: sweepCron
    keyVaultUri: keyVault.outputs.keyVaultUri
  }
}

module appService 'modules/appservice.bicep' = {
  name: 'appservice'
  params: {
    planName: '${baseName}-api-plan'
    webAppName: '${baseName}-api'
    location: location
    tags: tags
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    sqlServerFqdn: sql.outputs.serverFqdn
    sqlDatabaseName: sql.outputs.databaseName
    fulltextEnabled: fulltextEnabled
    searchEndpoint: searchEndpoint
    searchIndexName: searchIndexName
    azureOpenAiEndpoint: azureOpenAiEndpoint
    azureOpenAiChatDeployment: chatDeploymentName
    azureOpenAiEmbeddingDeployment: embeddingDeploymentName
    docIntelEndpoint: docIntelEndpoint
    consoleOrigin: consoleOrigin
    keyVaultUri: keyVault.outputs.keyVaultUri
  }
}

// RBAC: data-plane roles for the managed identities. SQL database access is
// NOT granted here — run the T-SQL in infra/README.md (CREATE USER ... FROM
// EXTERNAL PROVIDER) after deployment.
module roles 'modules/roles.bicep' = {
  name: 'rbac-core'
  params: {
    storageAccountName: storage.outputs.storageAccountName
    keyVaultName: keyVault.outputs.keyVaultName
    functionAppPrincipalId: functions.outputs.principalId
    webAppPrincipalId: appService.outputs.principalId
  }
}

module rolesSearch 'modules/roles-search.bicep' = if (deploySearch) {
  name: 'rbac-search'
  params: {
    searchServiceName: search!.outputs.name
    webAppPrincipalId: appService.outputs.principalId
  }
}

module rolesOpenAi 'modules/roles-openai.bicep' = if (deployOpenAI) {
  name: 'rbac-openai'
  params: {
    openAiAccountName: openAi!.outputs.name
    webAppPrincipalId: appService.outputs.principalId
  }
}

// web app MSI -> Cognitive Services User on the Document Intelligence account.
// The Static Web App identity is granted nothing extra (it calls the API over HTTPS).
module rolesDocIntel 'modules/roles-docintel.bicep' = if (deployDocIntel) {
  name: 'rbac-docintel'
  params: {
    docIntelAccountName: docIntel!.outputs.name
    webAppPrincipalId: appService.outputs.principalId
  }
}

// ----------------------------- outputs --------------------------------------

@description('Fully qualified domain name of the SQL logical server (SQL_SERVER).')
output sqlServerFqdn string = sql.outputs.serverFqdn

@description('Name of the ingestion function app.')
output functionAppName string = functions.outputs.functionAppName

@description('Name of the FastAPI web app.')
output webAppName string = appService.outputs.webAppName

@description('Default hostname of the research console Static Web App; empty when deployStaticWebApp = false.')
output staticWebAppHostname string = deployStaticWebApp ? staticWebApp!.outputs.defaultHostName : ''

@description('Azure AI Document Intelligence endpoint (DOCUMENT_INTELLIGENCE_ENDPOINT); empty when deployDocIntel = false.')
output docIntelEndpoint string = docIntelEndpoint

@description('Azure AI Search endpoint (SEARCH_ENDPOINT); empty when deploySearch = false.')
output searchEndpoint string = searchEndpoint

@description('Name of the storage account holding the ingestion containers.')
output storageAccountName string = storage.outputs.storageAccountName

@description('Key Vault URI (KEY_VAULT_URI).')
output keyVaultUri string = keyVault.outputs.keyVaultUri

@description('Application Insights connection string.')
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
