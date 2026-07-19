// App Service: Linux B1 plan + Python 3.11 web app for the FastAPI api/ package.
//
// NOTE: authentication is platform-level Easy Auth (Microsoft Entra), configured
// post-deploy — it needs an Entra app registration, which Bicep at resource-group
// scope cannot create. Commands in infra/README.md "Configure Easy Auth".

@description('Name of the Linux App Service plan.')
param planName string

@description('Name of the web app (globally unique).')
param webAppName string

@description('Azure region.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Application Insights connection string.')
param appInsightsConnectionString string

@description('SQL server FQDN (SQL_SERVER).')
param sqlServerFqdn string

@description('SQL database name (SQL_DATABASE).')
param sqlDatabaseName string

@description('Whether SQL full-text search is available (FULLTEXT_ENABLED).')
param fulltextEnabled bool = true

@description('Azure AI Search endpoint (SEARCH_ENDPOINT); empty when Search is not deployed.')
param searchEndpoint string = ''

@description('Azure AI Search index name (SEARCH_INDEX).')
param searchIndexName string = 'con-records'

@description('Azure OpenAI endpoint (AZURE_OPENAI_ENDPOINT); empty when Azure OpenAI is not deployed.')
param azureOpenAiEndpoint string = ''

@description('Chat model deployment name (AZURE_OPENAI_CHAT_DEPLOYMENT).')
param azureOpenAiChatDeployment string = 'gpt-4o-mini'

@description('Embedding model deployment name (AZURE_OPENAI_EMBEDDING_DEPLOYMENT).')
param azureOpenAiEmbeddingDeployment string = 'text-embedding-3-small'

@description('Azure AI Document Intelligence endpoint (DOCUMENT_INTELLIGENCE_ENDPOINT); empty when Document Intelligence is not deployed. The API authenticates with its managed identity (Cognitive Services User role) — no key is stored here; a DOCUMENT_INTELLIGENCE_KEY would only be an out-of-band Key Vault-referenced fallback.')
param docIntelEndpoint string = ''

@description('Origin of the research console for CORS (CONSOLE_ORIGIN), e.g. https://<name>.azurestaticapps.net. Empty when the Static Web App is not deployed. Add custom-domain origins to the API CORS config separately.')
param consoleOrigin string = ''

@description('Key Vault URI (KEY_VAULT_URI); optional fallback source for secrets.')
param keyVaultUri string = ''

@description('App Service plan SKU. F1 (Free) works for pilot use — 60 CPU-min/day, no Always-On, cold starts; B1 (~$13/mo) for steady state.')
@allowed(['F1', 'B1'])
param planSku string = 'B1'

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  kind: 'linux'
  sku: {
    name: planSku
    tier: planSku == 'F1' ? 'Free' : 'Basic'
  }
  properties: {
    reserved: true // Linux
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  tags: tags
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appCommandLine: 'python3 -m gunicorn -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 api.main:app'
      alwaysOn: planSku != 'F1' // Always On is not supported on the Free tier
      minTlsVersion: '1.2'
      ftpsState: 'FtpsOnly'
      appSettings: [
        {
          name: 'SQL_SERVER'
          value: sqlServerFqdn
        }
        {
          name: 'SQL_DATABASE'
          value: sqlDatabaseName
        }
        {
          name: 'FULLTEXT_ENABLED'
          value: toLower(string(fulltextEnabled))
        }
        {
          name: 'SEARCH_ENDPOINT'
          value: searchEndpoint
        }
        {
          name: 'SEARCH_INDEX'
          value: searchIndexName
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: azureOpenAiEndpoint
        }
        {
          name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
          value: azureOpenAiChatDeployment
        }
        {
          name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
          value: azureOpenAiEmbeddingDeployment
        }
        {
          // Document Intelligence endpoint; the API calls it with its MSI
          // (DefaultAzureCredential) — no key here. See infra/README.md.
          name: 'DOCUMENT_INTELLIGENCE_ENDPOINT'
          value: docIntelEndpoint
        }
        {
          // Static Web App origin, for the API's CORS allow-list.
          name: 'CONSOLE_ORIGIN'
          value: consoleOrigin
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'KEY_VAULT_URI'
          value: keyVaultUri
        }
        {
          // Oryx builds requirements.txt during zip deploy (az webapp deploy / az webapp up).
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
    }
  }
}

output webAppName string = webApp.name
output principalId string = webApp.identity.principalId
output defaultHostName string = webApp.properties.defaultHostName
