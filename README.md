# BankID Connect Integration

BankID authentication integration for Amazon Connect with PII-safe authentication flow.

## Overview

This project implements BankID authentication for customer verification during Amazon Connect calls, with a focus on security and GDPR compliance.

### Key Features

- 🔒 **PII-Safe Authentication**: No personal information disclosed before identity verification
- ✅ **Finnish BankID Support**: Full integration with Swedish/Finnish BankID systems
- 🔄 **Real-time Polling**: Status checks every 2 seconds for responsive authentication
- 📱 **Mobile App Integration**: Push notifications to customer's BankID app
- 🎯 **Forethought & Zendesk**: Seamless integration with existing contact center stack

## Architecture

```
Customer Call → Amazon Connect
                    ↓
            [fetchCustomerData Lambda] (Silent lookup)
                    ↓
            [bankIDAuthenticateLambda] (Initiate auth)
                    ↓
            [bankIDStatusCheckLambda] (Poll status)
                    ↓
            [Verified ✓] → Continue with personalized service
```

## Repository Structure

```
├── lambdas/
│   ├── bankIDAuthenticateLambda.py    # Initiate BankID authentication
│   └── bankIDStatusCheckLambda.py     # Check authentication status
├── docs/
│   ├── finnish_bankid_implementation.md  # Full implementation guide
│   ├── bankid_pii_security_guide.md      # PII security best practices
│   └── bankid_connect_integration_plan.md # Integration plan
├── templates/
│   └── sam-template.yaml              # AWS SAM deployment template
└── README.md
```

## Quick Start

### Prerequisites

- AWS Account with Lambda and Secrets Manager access
- Amazon Connect instance
- BankID test credentials (from demo.bankid.com)
- Python 3.11+

### Deployment

1. **Store BankID credentials in AWS Secrets Manager:**

```bash
aws secretsmanager create-secret \
  --name finnish-bankid-test-credentials \
  --secret-string file://secrets.json \
  --region eu-west-2
```

2. **Deploy Lambda functions:**

```bash
cd templates
sam build
sam deploy --guided
```

3. **Configure Amazon Connect:**
   - Import contact flow
   - Link Lambda functions
   - Test with BankID test credentials

## Security Principles

### 🔒 Core Rule: NO PII BEFORE AUTHENTICATION

**Before authentication:**
- ✅ Generic prompts only: "Check your BankID app"
- ✅ Silent data lookup (store, don't speak)
- ❌ NO customer names, dates of birth, or personal details

**After successful authentication:**
- ✅ Personalized greeting: "Thank you, [FirstName]"
- ✅ Access to account information
- ✅ Full service capabilities

**On authentication failure:**
- ✅ Generic error message
- ❌ NO PII disclosed
- ✅ Transfer to agent for manual verification

## Documentation

- [Full Implementation Guide](docs/finnish_bankid_implementation.md) - Complete technical documentation
- [PII Security Guide](docs/bankid_pii_security_guide.md) - Security best practices and compliance
- [Integration Plan](docs/bankid_connect_integration_plan.md) - Step-by-step deployment plan

## Testing

### Test Environment

1. Get test BankID from: https://demo.bankid.com
2. Install test BankID mobile app
3. Use test personal numbers provided
4. Test against BankID test API endpoint

### Test Scenarios

- ✅ Successful authentication flow
- ✅ Authentication timeout
- ✅ User cancellation
- ✅ Unknown phone number
- ✅ PII disclosure validation (critical!)

## Cost Estimate

**AWS (per 1,000 authentications):**
- Lambda invocations: ~$0.02
- Secrets Manager: $0.40/month
- CloudWatch Logs: ~$0.50
- **Total:** ~$0.92 per 1,000 authentications

## Support

- **BankID Documentation**: https://developers.bankid.com/
- **AWS Lambda**: https://docs.aws.amazon.com/lambda/
- **Amazon Connect**: https://docs.aws.amazon.com/connect/

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

---

**Status**: ✅ Ready for test environment deployment

**Next Steps**:
1. Register for BankID test access
2. Deploy Lambda functions
3. Configure Amazon Connect flow
4. End-to-end testing
