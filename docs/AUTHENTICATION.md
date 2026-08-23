# Authentication and Authorization

## User experience

Amazon Cognito is the sole identity authority for the application. Native
registration requires Email, First Name (`given_name`), Last Name
(`family_name`) and a password. Cognito sends a confirmation code to the email;
the user cannot obtain a normal authenticated session until verification.

The SPA is a public client and therefore has no client secret. It uses Cognito
managed login with OAuth 2.0 authorization-code flow plus PKCE. Tokens are kept
out of the repository and are never logged. Logout clears the local session and
uses Cognito's logout endpoint.

Google is configured as a Cognito identity provider for the HD external-account
rubric row. Google still returns through Cognito, so API Gateway has one issuer
and audience regardless of login method.

## JWT trust boundary

API Gateway HTTP API must validate:

- issuer: `https://cognito-idp.ap-southeast-2.amazonaws.com/<user-pool-id>`;
- audience: the SPA user-pool client ID;
- identity source: `$request.header.Authorization`;
- signature, token expiry and issuer/audience before Lambda invocation.

Lambda reads only the validated `requestContext.authorizer.jwt.claims` values.
It still rejects missing `sub` defensively. Request JSON can never choose the
owner subject or notification email.

## Google setup requiring a team member

The deployment needs a Google OAuth Web Application client created in a Google
account controlled by the team. A student must:

1. create/select the Google Cloud project;
2. configure the OAuth consent screen for the team/demo users;
3. create a Web Application OAuth client;
4. add Cognito's exact redirect URI:
   `https://<domain-prefix>.auth.ap-southeast-2.amazoncognito.com/oauth2/idpresponse`;
5. provide the client ID and secret only as `NoEcho` CloudFormation deployment
   inputs;
6. never save those values in Git, `.env.example`, screenshots, reports or
   `samconfig.toml`;
7. test one real Google login and logout after deployment.

The CloudFormation template deliberately has no placeholder default for these
two credentials. Deployment must stop instead of silently omitting Google and
losing the HD rubric functionality.

## IAM separation

`infrastructure/auth-and-iam.json` creates three Lambda roles:

- Core API: media/dedup/subscription CRUD, private presigning/deletion and SNS
  subscription/publish actions.
- Media processor: original read, thumbnail write, media state transitions,
  model read and notification publish.
- Temporary query: query-image read/delete, model read, media scan and result
  media read only.

No inline statement contains `Action: "*"`. Basic Lambda logging uses AWS's
standard execution managed policy. The sole `Resource: "*"` statement contains
only SNS `GetSubscriptionAttributes`, `SetSubscriptionAttributes` and
`Unsubscribe`, whose AWS IAM definitions do not support resource-level
authorization. SNS `Subscribe` and `Publish` remain restricted to the configured
topic ARN, and application state stores only subscriptions created for that
topic.

## Cost/safety

Cognito native-user and managed-login resources are serverless and no SMS MFA
is enabled. Email uses `COGNITO_DEFAULT`; demo traffic must remain inside the
account's free-plan quotas. The user pool has deletion protection and retain
policies to avoid accidental identity loss. No AWS resources have been created
by this document/template stage.
