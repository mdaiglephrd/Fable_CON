// Azure OpenAI account (Microsoft.CognitiveServices, kind OpenAI) with
// gpt-4o-mini + text-embedding-3-small Standard deployments.
//
// Deployed only when deployOpenAI = true in main.bicep: model availability and
// quota vary by region/subscription — see infra/README.md.

@description('Azure OpenAI account name (globally unique; also used as the custom subdomain).')
param accountName string

@description('Azure region (must offer the requested models — check availability).')
param location string

@description('Tags applied to all resources.')
param tags object = {}

@description('Deployment name for the chat model (AZURE_OPENAI_CHAT_DEPLOYMENT).')
param chatDeploymentName string = 'gpt-4o-mini'

@description('gpt-4o-mini model version.')
param chatModelVersion string = '2024-07-18'

@description('Capacity (thousands of tokens-per-minute) for the chat deployment.')
param chatCapacity int = 8

@description('Deployment name for the embedding model (AZURE_OPENAI_EMBEDDING_DEPLOYMENT).')
param embeddingDeploymentName string = 'text-embedding-3-small'

@description('text-embedding-3-small model version.')
param embeddingModelVersion string = '1'

@description('Capacity (thousands of tokens-per-minute) for the embedding deployment.')
param embeddingCapacity int = 50

resource account 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    // Custom subdomain is required for Entra ID (DefaultAzureCredential) auth.
    customSubDomainName: toLower(accountName)
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: account
  name: chatDeploymentName
  sku: {
    name: 'Standard'
    capacity: chatCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o-mini'
      version: chatModelVersion
    }
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: account
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: embeddingCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: embeddingModelVersion
    }
  }
  // Azure OpenAI processes one deployment operation at a time per account.
  dependsOn: [
    chatDeployment
  ]
}

output name string = account.name
output endpoint string = account.properties.endpoint
