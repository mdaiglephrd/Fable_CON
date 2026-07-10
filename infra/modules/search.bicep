// Azure AI Search — basic tier, system-assigned identity, AAD + API-key auth.
// The index (con-records) is created by api/search_sync.py, not by Bicep.

@description('Search service name (lowercase letters/digits/dashes, globally unique).')
param searchServiceName string

@description('Azure region.')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Semantic ranker plan. "free" caps at 1,000 requests/month; "standard" bills per request.')
@allowed(['disabled', 'free', 'standard'])
param semanticSearch string = 'free'

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: toLower(searchServiceName)
  location: location
  tags: tags
  sku: {
    name: 'basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    semanticSearch: semanticSearch
    // Allow both API keys and Entra ID tokens on the data plane: the API uses
    // DefaultAzureCredential (RBAC) but SEARCH_API_KEY remains a supported fallback.
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

output name string = searchService.name
output endpoint string = 'https://${searchService.name}.search.windows.net'
output principalId string = searchService.identity.principalId
