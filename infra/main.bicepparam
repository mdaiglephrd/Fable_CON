// Example parameters for infra/main.bicep.
// Copy/edit, then deploy:
//   az deployment group create -g <resource-group> -f infra/main.bicep -p infra/main.bicepparam
using './main.bicep'

param namePrefix = 'gacon'
param environment = 'dev'

// Region defaults to the resource group location; uncomment to override.
// param location = 'eastus2'

// --- Azure SQL Entra administrator (required) --------------------------------
// Object ID + display name of the user or group that administers the SQL server.
//   group: az ad group show --group <name> --query id -o tsv
//   user:  az ad signed-in-user show --query id -o tsv
param sqlAdminObjectId = '<your-entra-admin-object-id>'
param sqlAdminLogin = '<your-entra-admin-login>' // e.g. 'gacon-sql-admins' or 'admin@contoso.com'
param sqlAdminPrincipalType = 'Group' // 'User' | 'Group' | 'Application'

// --- Options ------------------------------------------------------------------
param enablePublicNetworkAccess = true // false once private endpoints are set up
param deploySearch = true // AI Search basic (~$75/mo) — the biggest fixed cost
param searchSemanticSearch = 'free' // 'disabled' | 'free' | 'standard'
param deployOpenAI = false // enable in a region with gpt-4o-mini + text-embedding-3-small quota
// param openAiChatCapacity = 8
// param openAiEmbeddingCapacity = 50
// param sweepCron = '0 0 6 * * *'
// param fulltextEnabled = true
// param logRetentionDays = 30
