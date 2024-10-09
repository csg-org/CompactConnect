<!--
    HomeStateBlock.vue
    CompactConnect

    Created by InspiringApps on 10/3/2024.
-->

<template>
    <div class="home-state-block-container">
        <div class="home-state-img-container">
            <img class="home-state-img" src="@assets/images/white-ellipse.svg" alt="Privilege List Logo" />
        </div>
        <div class="home-state-title">
            Home State
        </div>
        <div class="home-state-name">
            {{stateName}}
        </div>
    </div>
</template>

<script lang="ts" src="./HomeStateBlock.ts"></script>
<style scoped lang="less" src="./HomeStateBlock.less"></style>
