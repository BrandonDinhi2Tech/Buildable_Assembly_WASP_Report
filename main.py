import item
import assembly


if __name__ == "__main__":
    item.entire_inventory_api_call('item_list.csv')
    item.inventory_to_database('item_list.csv')
    assembly.update_bom_table()