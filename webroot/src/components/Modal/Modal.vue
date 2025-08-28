<!--
    Modal.vue
    inHere

    Created by InspiringApps on 5/22/2020.
-->

<template>
    <div>
        <Transition name="fade">
            <div
                class="modal-mask"
                :class="{ 'bg-close': closeOnBackgroundClick }"
                @click.self="closeOnBackgroundClick ? closeModal() : null"
                @keyup.enter="closeOnBackgroundClick ? closeModal() : null"
            >
                <div
                    class="modal-container"
                    :class="{ 'modal-error': isErrorModal }"
                    role="dialog"
                    aria-modal="true"
                    :aria-labelledby="titleId"
                >
                    <div class="header-container">
                        <h1 v-if="displayTitle" class="modal-title">{{ displayTitle }}</h1>
                        <InputButton
                            label="X"
                            v-if="hasCloseIcon"
                            aria-label="close modal"
                            class="icon icon-close-modal"
                            @click="closeModal"
                        />
                    </div>
                    <div :class="{ 'header-fixed': !!$slots['header-fixed'] }">
                        <slot name="header-fixed"></slot>
                    </div>
                    <form @submit.prevent>
                        <div ref="modalContent" class="modal-content" tabindex="0">
                            <slot name="content"></slot>
                        </div>
                        <div
                            v-if="showActions && !isLogoutOnly"
                            class="modal-actions"
                        >
                            <slot name="actions">
                                <InputButton
                                    aria-label="accept and close"
                                    label="OK"
                                    @click="closeModal"
                                />
                            </slot>
                        </div>
                        <div
                            v-if="isLogoutOnly"
                            class="modal-actions"
                        >
                            <InputButton
                                aria-label="logout"
                                label="Logout"
                                @click="logout"
                            />
                        </div>
                    </form>
                </div>
            </div>
        </Transition>
    </div>
</template>

<script lang="ts" src="./Modal.ts"></script>
<style scoped lang="less" src="./Modal.less"></style>
