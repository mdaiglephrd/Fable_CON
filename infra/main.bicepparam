// Example parameters for infra/main.bicep.
// Copy/edit, then deploy:
//   az deployment group create -g <resource-group> -f infra/main.bicep -p infra/main.bicepparam
using './main.bicep'

param namePrefix = 'gacon'
param environment = 'dev'

// Region defaults to the resource group location; uncomment to override.
param location = 'eastus2'

// --- Azure SQL Entra administrator (required) --------------------------------
// Object ID + display name of the user or group that administers the SQL server.
//   group: az ad group show --group <name> --query id -o tsv
//   user:  az ad signed-in-user show --query id -o tsv
param sqlAdminObjectId = 'f5c31594-e092-4b56-8fb5-85ecc13c6b96'
param sqlAdminLogin = 'mdai@phrd.com' // e.g. 'gacon-sql-admins' or 'admin@contoso.com'
param sqlAdminPrincipalType = 'Group' // 'User' | 'Group' | 'Application'

// --- Options ------------------------------------------------------------------
param enablePublicNetworkAccess = true // false once private endpoints are set up
param deploySearch = false // AI Search basic (~$75/mo); false = free posture (SQL full-text covers keyword search)
param searchSemanticSearch = 'free' // 'disabled' | 'free' | 'standard'
param deployOpenAI = false // enable in a region with gpt-4o-mini + text-embedding-3-small quota
// param openAiChatCapacity = 8
// param openAiEmbeddingCapacity = 50
// param sweepCron = '0 0 6 * * *'
// param fulltextEnabled = true
// param logRetentionDays = 30

// --- Research layer (v2): console + document-text extraction -----------------
param deployStaticWebApp = true // Azure Static Web App (Free) for the React console (web/)
// SWA is region-limited; override if the RG region is unsupported (e.g. westus2, eastus2, centralus, westeurope, eastasia)
param staticWebAppLocation = 'eastus2'
param computeLocation = 'westus2' // App Service quota was denied in eastus2; try a different region independently of the rest of the stack
param deployDocIntel = true // Azure AI Document Intelligence for the document-text step
param docIntelSku = 'F0' // 'F0' free (500 pages/mo) | 'S0' standard (for the initial corpus backfill)
param sqlUseFreeOffer = true // Azure SQL Database free offer (GP serverless free monthly limits)
param appServicePlanSku = 'F1' // F1 = free pilot (60 CPU-min/day, no Always-On); default B1 (~$13/mo)
