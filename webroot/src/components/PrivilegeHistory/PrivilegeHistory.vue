<!--
    PrivilegeHistory.vue
    CompactConnect

    Created by InspiringApps on 3/26/2025.
-->

<template>
    <div class="history-container">
        <div v-for="(richEvent, idx) in preppedEvents" :key="idx" class="events">
            <StatusTimeBlock
                class="status-time-block"
                :isStartOfVisualBlock="richEvent.isStartOfVisualBlock"
                :isEndOfVisualBlock="richEvent.isEndOfVisualBlock"
                :event="richEvent.event"
                :isLastEvent="richEvent.isLastEvent"
            />
            <PrivilegeEventNode
                :event="richEvent.event"
                :eventLengthBucket="richEvent.eventLengthBucket"
                class="event-node"
            />
        </div>
        <div class="now-line">
            <div v-if="isActive" class="dot"></div>
            <div class="after-now">
                <div v-if="isActive" class="down-dipper">
                </div>
                <div class="today">{{$t('common.today')}}</div>
                <div v-if="isActive" class="exp-detail">
                    <div v-if="isExpirationUpcoming" class="exp-warning">
                        <img
                            src="@assets/icons/ico-caution.svg"
                            :alt="$t('common.caution')"
                            class="warning-logo"
                        />
                    </div>
                    <div class="exp-date">{{privilege.expireDateDisplay()}}</div>
                    <div class="exp-title">{{$t('licensing.expiration')}}</div>
                    <div v-if="isExpirationUpcoming" class="exp-text">{{expirationText}}</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegeHistory.ts"></script>
<style scoped lang="less" src="./PrivilegeHistory.less"></style>
