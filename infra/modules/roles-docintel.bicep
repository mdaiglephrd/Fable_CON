// RBAC on the Document Intelligence account (deployed only when deployDocIntel = true):
//   web app (FastAPI API) -> Cognitive Services User (analyze documents via MSI)
//
// Cognitive Services User is the least-privilege data-plane role for calling the
// Document Intelligence analyze APIs with DefaultAzureCredential (no API key).
// Role definition ID a97b65f3-24c7-4388-baec-2e87135dc908 — verified against the
// Azure built-in roles reference (AI + machine learning).
//
// The Static Web App identity is intentionally granted NOTHING here: the console
// calls the API over HTTPS and never touches Document Intelligence directly.

@description('Document Intelligence account name.')
param docIntelAccountName string

@description('Principal ID of the web app system-assigned identity.')
param webAppPrincipalId string

var cognitiveServicesUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'a97b65f3-24c7-4388-baec-2e87135dc908'
)

resource docIntelAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: docIntelAccountName
}

resource webAppCognitiveServicesUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(docIntelAccount.id, webAppPrincipalId, cognitiveServicesUserRoleId)
  scope: docIntelAccount
  properties: {
    roleDefinitionId: cognitiveServicesUserRoleId
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}
