<template>
  <div id="app">
    <!-- Tarjeta 1: Selección de Tablas y Campos -->
    <div class="card">
      <div class="card-header">
        <h3>Selección de Tablas y Campos</h3>
      </div>
      <div class="card-body">
        <!-- Selector de tablas -->
        <div class="table-selector">
          <label for="tableSelect">Seleccionar Tabla:</label>
          <select 
            id="tableSelect" 
            v-model="selectedTable" 
            class="table-select"
          >
            <option value="">Seleccione una tabla</option>
            <option 
              v-for="(table, tableName) in tables" 
              :key="tableName" 
              :value="tableName"
            >
              {{ tableName }}
            </option>
          </select>
        </div>

        <!-- Lista de campos de la tabla seleccionada -->
        <div v-if="selectedTable" class="campos-container">
          <h4>Campos de {{ selectedTable }}:</h4>
          <draggable
            :list="tables[selectedTable].campos"
            :group="{ name: 'fields', pull: 'clone', put: false }"
            item-key="id"
            class="campos-list"
          >
            <template #item="{ element }">
              <div class="campo-draggable">
                <span class="campo-nombre">{{ element.nombre }}</span>
                <span class="campo-tipo">({{ element.tipo }})</span>
              </div>
            </template>
          </draggable>
        </div>
      </div>
    </div>

    <!-- Tarjeta 2: Grilla de Datos -->
    <div class="card">
      <div class="card-header">
        <h3>Grilla de Datos</h3>
      </div>
      <div class="card-body">
        <!-- Área donde se soltarán los campos -->
        <div class="drop-zone">
          <h4>Arrastre los campos aquí:</h4>
          <draggable
            v-model="selectedCampos"
            :group="{ name: 'fields', pull: true, put: true }"
            item-key="id"
            class="selected-campos"
            @change="fetchFilteredData"
          >
            <template #item="{ element }">
              <div class="campo-selected">
                <span>{{ element.nombre }}</span>
                <button 
                  @click="removeCampo(element)" 
                  class="remove-campo"
                >
                  ×
                </button>
              </div>
            </template>
          </draggable>
        </div>

        <!-- Tabla con los datos -->
        <div v-if="selectedCampos.length > 0" class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th v-for="campo in selectedCampos" :key="campo.id">
                  {{ campo.nombre }}
                  <span class="column-type">{{ campo.tipo }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in filteredData" :key="rowIndex">
                <td v-for="campo in selectedCampos" :key="campo.id">
                  {{ row[campo.nombre] || 'N/A' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="no-fields">
          Arrastre campos desde la lista para visualizar datos
        </p>
      </div>
    </div>

    <!-- Tarjeta 3: Filtros por Palabra -->
    <div class="card">
      <div class="card-header">
        <h3>Filtros por Palabra</h3>
      </div>
      <div class="card-body">
        <p>Arrastre los campos desde la lista para aplicar filtros por palabra:</p>
        <draggable
          v-model="filterCampos"
          :group="{ name: 'fields', pull: true, put: true }"
          item-key="id"
          class="selected-campos"
        >
          <template #item="{ element }">
            <div class="campo-selected">
              <span>{{ element.nombre }}</span>
              <input
                v-model="filterValues[element.nombre]"
                placeholder="Valor de filtro"
                class="filter-input"
              />
              <button 
                @click="removeFilterCampo(element)" 
                class="remove-campo"
              >
                ×
              </button>
            </div>
          </template>
        </draggable>
        <button @click="applyWordFilters" class="apply-filters-btn">Aplicar Filtros</button>
      </div>
    </div>
  </div>
</template>

<script>
import draggable from 'vuedraggable';
import axios from 'axios';

export default {
  name: 'App',
  components: {
    draggable
  },
  data() {
    return {
      selectedTable: '',
      selectedCampos: [],
      filterCampos: [], // Campos para filtros por palabra
      filterValues: {}, // Valores de los filtros por palabra
      tables: {}, // Tablas y campos cargados desde el backend
      filteredData: [] // Datos filtrados obtenidos del backend
    };
  },
  methods: {
    fetchTables() {
      axios.get('http://localhost:8000/tables')
        .then(response => {
          this.tables = response.data.tables;
        })
        .catch(error => {
          console.error('Error al obtener tablas y columnas:', error);
        });
    },
    removeFilterCampo(campo) {
      const index = this.filterCampos.indexOf(campo);
      if (index > -1) {
        this.filterCampos.splice(index, 1);
        delete this.filterValues[campo.nombre]; // Asegúrate de que esta línea termine con ;
      }
    },
    removeCampo(campo) {
      const index = this.selectedCampos.indexOf(campo);
      if (index > -1) {
        this.selectedCampos.splice(index, 1);
      }
    },
    applyWordFilters() {
      if (!this.selectedTable) {
        console.warn("Debe seleccionar una tabla antes de aplicar filtros.");
        return;
      }

      const filters = this.filterCampos.map(campo => ({
        nombre: campo.nombre,
        valor: this.filterValues[campo.nombre] || ""
      }));

      const selectedFields = this.selectedCampos.map(campo => campo.nombre);

      axios
        .post("http://localhost:8000/filtered-data", {
          table: this.selectedTable,
          filters,
          selected_fields: selectedFields // Enviar todos los campos seleccionados
        })
        .then(response => {
          if (response.data && response.data.data) {
            this.filteredData = response.data.data;
          }
        })
        .catch(error => {
          console.error("Error al aplicar filtros:", error);
        });
    },
    fetchFilteredData() {
      if (!this.selectedTable || this.selectedCampos.length === 0) {
        this.filteredData = [];
        return;
      }

      const selectedFields = this.selectedCampos.map(campo => campo.nombre);

      
      axios.post("http://localhost:8000/data", {
          table: this.selectedTable,
          selected_fields: selectedFields
        })
        .then(response => {
          if (response.data && response.data.data) {
            this.filteredData = response.data.data;
          }
        })
        .catch(error => {
          console.error("Error al obtener datos:", error);
          this.filteredData = [];
        });
    }
  },
  mounted() {
    this.fetchTables();
  }
};
</script>

<style scoped>
.card {
  margin: 1rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.card-header h3 {
  margin: 0;
  color: #333;
}

.table-selector {
  margin-bottom: 1rem;
}

.table-select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-top: 0.5rem;
}

.campos-container {
  margin-top: 1rem;
}

.campos-list {
  min-height: 50px;
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
}

.campo-draggable {
  padding: 0.5rem;
  margin: 0.5rem 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: move;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.campo-tipo {
  color: #666;
  font-size: 0.9em;
}

.drop-zone {
  margin-bottom: 1rem;
}

.selected-campos {
  min-height: 50px;
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 4px;
  border: 2px dashed #ccc;
}

.campo-selected {
  padding: 0.5rem;
  margin: 0.5rem 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.remove-campo {
  background: none;
  border: none;
  color: #ff4444;
  font-size: 1.2em;
  cursor: pointer;
  padding: 0 0.5rem;
}

.remove-campo:hover {
  color: #ff0000;
}

.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.data-table th,
.data-table td {
  padding: 0.75rem;
  border: 1px solid #ddd;
  text-align: left;
}

.data-table th {
  background: #f5f5f5;
  font-weight: bold;
}

.column-type {
  display: block;
  font-size: 0.8em;
  color: #666;
  font-weight: normal;
}

.data-table tr:nth-child(even) {
  background: #fafafa;
}

.no-fields {
  text-align: center;
  color: #666;
  padding: 1rem;
}

.campo-draggable:hover {
  background: #f0f0f0;
}
</style>