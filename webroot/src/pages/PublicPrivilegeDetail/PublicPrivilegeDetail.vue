<!--
    PublicPrivilegeDetail.vue
    CompactConnect

    Created by InspiringApps on 3/18/2025.
-->

<template>
    <div class="privilege-detail-container">
        <transition name="fade">
            <LoadingSpinner class="place-holder" v-show="isLoading"></LoadingSpinner>
        </transition>
        <div v-if="licenseeRecord" class="privilege-detail-content-container">
            <InputButton
                :label="$t('common.back')"
                :aria-label="$t('common.back')"
                :isTextLike="true"
                :shouldHideMargin="true"
                class="back-btn"
                @click="goBack"
            />
            <div class="privilege-detail-title">
                {{ privilegeTitle }}
            </div>
            <PrivilegeDetailBlock
                :privilege="privilege"
            />
        </div>
    </div>
</template>

<script lang="ts" src="./PublicPrivilegeDetail.ts"></script>
<style scoped lang="less" src="./PublicPrivilegeDetail.less"></style>
