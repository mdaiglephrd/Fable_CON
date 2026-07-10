// RBAC on the Azure OpenAI account (deployed only when deployOpenAI = true):
//   web app -> Cognitive Services OpenAI User (chat completions + embeddings)

@description('Azure OpenAI account name.')
param openAiAccountName string

@description('Principal ID of the web app system-assigned identity.')
param webAppPrincipalId string

var cognitiveServicesOpenAiUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
)

resource openAiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: openAiAccountName
}

resource webAppOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAiAccount.id, webAppPrincipalId, cognitiveServicesOpenAiUserRoleId)
  scope: openAiAccount
  properties: {
    roleDefinitionId: cognitiveServicesOpenAiUserRoleId
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
  }
}
