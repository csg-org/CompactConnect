<!--
    PrivilegeHistory.vue
    CompactConnect

    Created by InspiringApps on 3/26/2025.
-->

<template>
    <div class="history-container">
        <ul
            :aria-label="$t('licensing.events')"
        >
            <li
                v-for="(richEvent, idx) in preppedEvents"
                :key="idx"
                class="events"
                :aria-label="$t('licensing.eventNodeLabel', { eventNameDisplay, eventDate })"
            >
                <div class="timeline-line" />
                <PrivilegeEventNode
                    :event="richEvent.event"
                    :eventLengthBucket="richEvent.eventLengthBucket"
                    class="event-node"
                />
            </li>
        </ul>
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
