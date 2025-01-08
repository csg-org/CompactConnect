<!--
    UpdateMilitaryStatus.vue
    CompactConnect

    Created by InspiringApps on 12/20/2024.
-->

<template>
    <div class="update-military-status-container">
        <div class="update-military-status-content-container">
            <InputButton
                :label="$t('common.back')"
                :aria-label="$t('common.back')"
                :isTextLike="true"
                :shouldHideMargin="true"
                class="back-btn"
                @click="goBack"
            />
            <div class="update-military-status-title">
                {{ $t('military.updateMilitaryStatusTitle') }}
            </div>
            <div class="core-info-block">
                <form @submit.prevent="handleSubmit">
                    <div class="title-row">
                        {{attestationTitleText}}
                    </div>
                    <div class="attestation-section">
                        <InputRadioGroup :formInput="formData.affiliationType" />
                    </div>
                    <div class="document-section">
                        <div class="title-row">
                            {{documentProofLabel}}
                        </div>
                        <div class="file-instructions">
                            {{ $t('military.fileInstructions') }}
                        </div>
                        <InputFile :formInput="formData.document" />
                    </div>
                    <div class="button-row">
                        <InputSubmit
                            :formInput="formData.submit"
                            :label="$t('common.submit')"
                            :aria-label="$t('common.submit')"
                        />
                    </div>
                </form>
            </div>
        </div>
   </div>
</template>

<script lang="ts" src="./UpdateMilitaryStatus.ts"></script>
<style scoped lang="less" src="./UpdateMilitaryStatus.less"></style>
