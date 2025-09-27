# CDK Pipeline Architecture Design

[View Pipeline Architecture (PDF)](./pipeline-architecture.pdf)

## Overview

The CompactConnect CI/CD pipeline architecture implements an optimized deployment strategy built around AWS CDK
Pipelines (see https://docs.aws.amazon.com/cdk/v2/guide/cdk_pipeline.html). It follows a multi-pipeline approach with
separate backend and frontend pipelines to improve deployment speed, reliability, and security.

## Key Components

### Backend Pipelines

There are different backend pipelines for each environment, defined as part of this CDK app. Those pipelines deploy
infrastructure resources and backend components to environment-specific application AWS accounts.

### Frontend Pipelines

There are also different frontend pipelines for each environment. These pipelines are defined as part of the separate
[CompactConnect UI App](../../../compact-connect-ui-app/README.md). The frontend pipelines deploy application hosting
infrastructure to the environment-specific application AWS accounts, based on backend configuration values, provide
by the backend deploy process.

### Deployment Resources Stack



- **Deployment Resources Stack**: Shared resources used by all pipeline stacks across all environments
- **Environments**: Test, Beta, and Production environments

## Pipeline Flow

1. GitHub push → Backend Pipeline
2. Backend Pipeline successful completion → Trigger Frontend Pipeline
3. Frontend Pipeline deploys web application using configuration values from Backend

Commits pushed to the 'development' branch trigger the test pipelines. Commits pushed to the 'main' branch trigger the
beta and prod pipelines.

## Self-Mutation Feature and Optimization

### Understanding CDK Pipeline Self-Mutation

AWS CDK Pipelines include a powerful "self-mutation" feature that allows the pipeline to update itself. When code
changes affecting the pipeline's structure are pushed, the pipeline:

1. Executes with its current configuration
2. Synthesizes CloudFormation templates for all stacks in the app
3. Deploys a "self-mutation" step that updates the pipeline's own definition
4. Continues deployment with the updated pipeline definition

While powerful, this feature presents challenges:

1. **Performance Impact**: By default, CDK synthesizes all stacks in the application even when only one pipeline needs
   to be updated. This can be extremely slow, especially for complex applications.

2. **Unnecessary Processing**: Every pipeline synthesis includes bundling operations (like frontend builds) even when
   those components aren't changing.

### The SynthSubstituteStage and SynthSubstituteStack Solution

To address these challenges, we've implemented the `SynthSubstituteStage` and `SynthSubstituteStack` classes that act
as lightweight placeholders during the synthesis process:

#### How It Works

1. During pipeline synthesis, we pass in cdk context variables to determine which specific pipeline is being
   synthesized.

2. For any stage that isn't part of the current pipeline being synthesized, we replace it with a `SynthSubstituteStage`
   containing a minimal `SynthSubstituteStack`.

3. The substitute stack synths a single SSM parameter resource, dramatically reducing synthesis time compared to full application stacks.

## Implementation Details

The substitution mechanism relies on CDK context values which we pass in during the CDK synth step of the pipeline definition (see the [BackendPipeline](../backend_pipeline.py) and [FrontendPipeline](../frontend_pipeline.py) class constructors, specifically the `synth.commands` property):

```python
commands=[
    ... other commands
    # Only synthesize the specific pipeline stack needed
    f'cdk synth --context pipelineStack={pipeline_stack_name} --context action=pipelineSynth',
],
```
The following context values are used to determine which pipeline to fully synthesize:

- `action`: Specifies the current action (e.g., `pipelineSynth`, `bootstrapDeploy`)
- `pipelineStack`: The specific pipeline stack being synthesized

In the pipeline stack classes, the `_determine_backend_stage` and `_determine_frontend_stage` methods handle the stage substitution logic:

```python
def _determine_backend_stage(self, construct_id, app_name, environment_name, environment_context):
    # Check if we're in pipeline synthesis mode and if we're synthesizing this specific pipeline
    action = self.node.try_get_context('action')
    pipeline_stack_name = self.node.try_get_context('pipelineStack')

    # Use substitute stage if not synthesizing this specific pipeline or during bootstrap
    if (action == PIPELINE_SYNTH_ACTION and pipeline_stack_name != self.stack_name) or action == BOOTSTRAP_DEPLOY_ACTION:
        return SynthSubstituteStage(
            self,
            'SubstituteBackendStage',
            environment_context=environment_context,
        )

    # Otherwise, use the real stage
    return BackendStage(
        self,
        construct_id,
        app_name=app_name,
        environment_name=environment_name,
        environment_context=environment_context,
    )
```

# Bootstrapping the piplines
See this [README.md](../../README.md) for details on performing a bootstrap deployment of the pipelines.
