// Core RBAC role assignments for the app managed identities:
//   function app -> Storage Blob Data Contributor (storage account)
//   function app -> Key Vault Secrets User        (key vault)
//   web app      -> Key Vault Secrets User        (key vault)
//
// Search / Azure OpenAI assignments live in roles-search.bicep / roles-openai.bicep
// (deployed conditionally). SQL database access is granted via T-SQL, not ARM —
// see infra/README.md.

@description('Storage account holding the ingestion containers.')
param storageAccountName string

@description('Key Vault name.')
param keyVaultName string

@description('Principal ID of the function app system-assigned identity.')
param functionAppPrincipalId string

@description('Principal ID of the web app system-assigned identity.')
param webAppPrincipalId string

// Built-in role definition IDs (see Azure built-in roles reference).
var storageBlobDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)
var keyVaultSecretsUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource functionStorageBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionAppPrincipalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageBlobDataContributorRoleId
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource functionKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionAppPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleId
    principalId: functionAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource webAppKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, webAppPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleId
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}
