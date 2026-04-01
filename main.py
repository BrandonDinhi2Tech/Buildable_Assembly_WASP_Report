import item
import assembly


if __name__ == "__main__":
    item.entire_inventory_api_call('item_list.csv')
    item.inventory_to_database('item_list.csv')
    assembly.assembly_api_call('800008')