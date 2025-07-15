<!--
    ExampleForm.vue
    InspiringApps modules

    Created by InspiringApps on 5/3/2021.
-->

<template>
    <Section class="section-example-form">
        <h2>{{ $t('styleGuide.exampleForm') }}</h2>
        <div class="example-form-container">
            <form @submit.prevent="handleSubmit">
                <InputText :formInput="formData.firstName" />
                <InputText :formInput="formData.lastName" />
                <InputText :formInput="formData.email" />
                <InputTextarea
                    :formInput="formData.description"
                    :shouldResizeY="true"
                />
                <InputSelect :formInput="formData.state" />
                <InputCheckbox :formInput="formData.isSubscribed" />
                <InputRadioGroup :formInput="formData.status" />
                <InputDate :formInput="formData.dob" />
                <InputFile :formInput="formData.documents" />
                <InputPassword
                    :formInput="formData.password"
                    :joiMessages="joiMessages"
                    :showEyeIcon="true"
                />
                <InputPhone :formInput="formData.phone" />
                <InputRange
                    :formInput="formData.happiness"
                    :showValueLabel="true"
                    :showTickMarks="true"
                    :tickInterval="5"
                    :showTickLabels="true"
                />
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading"
                />
            </form>
        </div>
    </Section>
</template>

<script lang="ts" src="./ExampleForm.ts"></script>
<style scoped lang="less" src="./ExampleForm.less"></style>
