<template>
  <li class="tree-list">
    {{ node.name }}
    <ul v-if="node.has_children">
      <tree-list
        v-for="node in node.children"
        :key="node.id"
        :href="item.href"
        :node="node"
      />
    </ul>
  </li>
</template>
<script>
module.exports = {
  name: 'tree-list',
  props: ['node'],
  data: function () {
    return {
      who: 'world'
    }
  }
}
</script>
<style>

</style>