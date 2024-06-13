<!--
    App.vue
    inHere

    Created by InspiringApps on 4/12/20.
    Copyright © 2024. InspiringApps. All rights reserved.
-->

<template>
    <div id="app">
        <PageContainer>
            <router-view v-slot="{ Component }">
                <transition name="fade" mode="out-in" @after-leave="$root.$emit('trigger-scroll-behavior')">
                    <component :is="Component" />
                </transition>
            </router-view>
        </PageContainer>
        <Modal
            v-if="showMessageModal"
            :closeOnBackgroundClick="!isErrorModal"
            :isErrorModal="isErrorModal"
            @close-modal="closeModal"
            :messages="messages"
        >
            <template v-slot:content>
                <ul>
                    <li v-for="(item, index) in messages" v-bind:key="index">{{ item.message }}</li>
                </ul>
            </template>
        </Modal>
    </div>
</template>

<script lang="ts" src="./App.ts"></script>
<!--
    Common LESS styles.
    Included here for build.
    The reason this isn't needed in every component during local development / testing
    is because the Webpack config is using the style-resources-loader package to inject.
-->
<style lang="less" src="@/styles.common/index.less"></style>
