<!--
    PrivilegeHistory.vue
    CompactConnect

    Created by InspiringApps on 3/26/2025.
-->

<template>
    <div class="history-container">
        <div v-for="(event, idx) in preppedEvents" :key="idx" class="events">
            <StatusTimeBlock
                class="status-time-block"
            />
            <EventNode
                :event="event"
                class="event-node"
            />
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegeHistory.ts"></script>
<style scoped lang="less" src="./PrivilegeHistory.less"></style>
