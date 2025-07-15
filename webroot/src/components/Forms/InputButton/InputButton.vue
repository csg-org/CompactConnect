<!--
    InputButton.vue
    inHere

    Created by InspiringApps on 5/27/2020.
-->

<template>
    <div class="input-container input-button-container" :class="{ 'no-margin': shouldHideMargin }">
        <input
            type="button"
            :id="id"
            ref="button"
            class="input-button"
            :class="{
                'no-text-transform': !shouldTransformText,
                'transparent': isTransparent,
                'text-like': isTextLike,
                'warning': isWarning,
            }"
            :value="label"
            v-bind:disabled="isEnabled === false ? true : false"
            @click="onClick($event)"
        />
    </div>
</template>

<script lang="ts" src="./InputButton.ts"></script>
<style scoped lang="less" src="./InputButton.less"></style>
